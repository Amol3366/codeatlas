"""BM25 keyword index (CLAUDE.md §3, §4 "Retrieval").

Runs alongside the vector store so users can find exact symbol names and paths.
rank-bm25 is in-memory, so the corpus is persisted to ``DATA_DIR`` as JSON and
the BM25 model is rebuilt lazily on load or after mutations.
"""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from app.interfaces import KeywordIndex
from app.models import Chunk, RetrievedChunk

if TYPE_CHECKING:
    from rank_bm25 import BM25Okapi

# Split identifiers into subtokens so `create_session`, `createSession`, and
# `create/session` all match a query for "create session".
_WORD_RE = re.compile(r"[A-Za-z0-9]+")
_CAMEL_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercased words plus identifier subtokens."""
    tokens: list[str] = []
    for word in _WORD_RE.findall(text):
        lowered = word.lower()
        tokens.append(lowered)
        for part in _CAMEL_RE.findall(word):
            part_lower = part.lower()
            if part_lower and part_lower != lowered:
                tokens.append(part_lower)
    return tokens


def _searchable_text(chunk: Chunk) -> str:
    parts = [chunk.path, chunk.symbol_name or "", chunk.summary or "", chunk.content]
    return " ".join(part for part in parts if part)


class BM25KeywordIndex(KeywordIndex):
    """Persistent BM25 keyword index over chunk text, paths, and symbols."""

    def __init__(self, persist_path: Path) -> None:
        self._persist_path = persist_path
        self._lock = threading.Lock()
        self._chunks: dict[str, Chunk] = {}
        self._ordered_ids: list[str] = []
        self._bm25: BM25Okapi | None = None
        self._load()

    def _load(self) -> None:
        if not self._persist_path.exists():
            return
        raw = json.loads(self._persist_path.read_text(encoding="utf-8"))
        for item in raw:
            chunk = Chunk.model_validate(item)
            if chunk.id not in self._chunks:
                self._ordered_ids.append(chunk.id)
            self._chunks[chunk.id] = chunk

    def _persist(self) -> None:
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [self._chunks[cid].model_dump() for cid in self._ordered_ids]
        self._persist_path.write_text(json.dumps(payload), encoding="utf-8")

    def _rebuild(self) -> None:
        from rank_bm25 import BM25Okapi

        corpus = [tokenize(_searchable_text(self._chunks[cid])) for cid in self._ordered_ids]
        # BM25Okapi requires a non-empty corpus.
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def add(self, chunks: Sequence[Chunk]) -> None:
        if not chunks:
            return
        with self._lock:
            for chunk in chunks:
                if chunk.id not in self._chunks:
                    self._ordered_ids.append(chunk.id)
                self._chunks[chunk.id] = chunk
            self._persist()
            self._bm25 = None  # invalidate; rebuilt lazily on next search

    def search(self, query: str, k: int) -> list[RetrievedChunk]:
        with self._lock:
            if self._bm25 is None:
                self._rebuild()
            if self._bm25 is None or not self._ordered_ids:
                return []
            scores = self._bm25.get_scores(tokenize(query))
            ranked = sorted(
                zip(self._ordered_ids, scores, strict=True),
                key=lambda pair: pair[1],
                reverse=True,
            )
            results: list[RetrievedChunk] = []
            for chunk_id, score in ranked[:k]:
                if score <= 0.0:
                    break
                results.append(RetrievedChunk(chunk=self._chunks[chunk_id], score=float(score)))
            return results
