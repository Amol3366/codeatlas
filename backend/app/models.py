"""Core data structures for CodeAtlas.

Contains the atomic :class:`Chunk` stored and retrieved (CLAUDE.md §5), the
input :class:`SourceFile` handed to a chunker, and the request/response schemas
that make up the HTTP API contract (CLAUDE.md §6).

Paths carried by these models are ALWAYS relative to the repo root — absolute
machine paths must never reach the index or the UI (CLAUDE.md §5).
"""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel, Field

Kind = Literal["code", "doc"]


def make_chunk_id(repo: str, path: str, start_line: int, end_line: int) -> str:
    """Return a deterministic id for a chunk.

    The id is a stable hash of ``repo + path + start_line + end_line`` so that
    re-indexing the same content updates the existing entry rather than creating
    a duplicate (CLAUDE.md §5).
    """
    raw = f"{repo}\x00{path}\x00{start_line}\x00{end_line}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


class SourceFile(BaseModel):
    """A single file selected by the walker, ready to be chunked.

    ``path`` is relative to the repo root; ``abs_path`` is resolved only for
    read-time access (e.g. code previews) and never stored on a chunk.
    """

    repo: str
    path: str
    abs_path: str
    content: str
    language: str | None
    kind: Kind
    commit_hash: str | None = None


class Chunk(BaseModel):
    """The atomic unit stored in the vector store and keyword index (CLAUDE.md §5)."""

    id: str
    repo: str
    path: str
    language: str | None
    kind: Kind
    symbol_name: str | None
    start_line: int
    end_line: int
    content: str
    summary: str | None = None
    commit_hash: str | None = None

    def embedding_text(self) -> str:
        """Text handed to the embedder.

        ``content`` alone, or ``summary + content`` when index-time enrichment
        produced a summary (CLAUDE.md §5).
        """
        if self.summary:
            return f"{self.summary}\n\n{self.content}"
        return self.content


class RetrievedChunk(BaseModel):
    """A chunk returned from retrieval together with its relevance score."""

    chunk: Chunk
    score: float


# ---------------------------------------------------------------------------
# API contract (CLAUDE.md §6)
# ---------------------------------------------------------------------------


class Source(BaseModel):
    """A cited source rendered in the frontend's Sources panel."""

    path: str
    start_line: int
    end_line: int
    symbol_name: str | None = None


class ChatMessage(BaseModel):
    """One turn of prior conversation history."""

    role: Literal["user", "assistant"]
    content: str


class IngestRequest(BaseModel):
    """Body of ``POST /ingest``."""

    path: str
    repo_label: str


class IngestResponse(BaseModel):
    """Response of ``POST /ingest`` — identifies the async indexing job."""

    job_id: str
    status: str


class IndexSummary(BaseModel):
    """Summary of the last successful index, surfaced by ``GET /status``."""

    repo_label: str
    path: str
    files_indexed: int
    chunks_indexed: int
    finished_at: str


class StatusResponse(BaseModel):
    """Response of ``GET /status`` — current job progress + last good index."""

    job_id: str | None = None
    state: Literal["idle", "running", "completed", "failed"] = "idle"
    message: str | None = None
    files_seen: int = 0
    files_indexed: int = 0
    chunks_indexed: int = 0
    error: str | None = None
    last_successful_index: IndexSummary | None = None


class FileInfo(BaseModel):
    """One indexed file with its chunk count (``GET /files``)."""

    repo: str
    path: str
    kind: Kind
    language: str | None
    chunk_count: int


class FilesResponse(BaseModel):
    """Response of ``GET /files``."""

    files: list[FileInfo] = Field(default_factory=list)
    total_files: int = 0
    total_chunks: int = 0


class ChatRequest(BaseModel):
    """Body of ``POST /chat``."""

    question: str
    history: list[ChatMessage] | None = None


class ChatResponse(BaseModel):
    """Final structured payload emitted after the ``/chat`` token stream."""

    answer: str
    sources: list[Source] = Field(default_factory=list)
