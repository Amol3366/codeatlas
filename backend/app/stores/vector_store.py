"""Chroma-backed :class:`VectorStore` (CLAUDE.md §3).

Chroma is the v1 vector store: zero-setup, local, persistent. Embeddings are
computed in the ingestion layer and passed in, so this module stays free of any
embedding provider. Chunk ``content`` is stored as the document; the remaining
:class:`Chunk` fields are stored as metadata and reconstructed on read.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from app.interfaces import VectorStore
from app.models import Chunk, FileInfo, Kind, RetrievedChunk

if TYPE_CHECKING:
    from chromadb.api import ClientAPI
    from chromadb.api.models.Collection import Collection

_COLLECTION_NAME = "codeatlas"
# Optional string metadata fields — omitted from Chroma when None (Chroma
# rejects None metadata values) and restored as None on read.
_OPTIONAL_STR_FIELDS = ("language", "symbol_name", "summary", "commit_hash")


class ChromaVectorStore(VectorStore):
    """Persistent semantic index over chunk embeddings, backed by Chroma."""

    def __init__(self, persist_dir: Path) -> None:
        self._persist_dir = persist_dir
        self._client: ClientAPI | None = None
        self._collection: Collection | None = None

    def _get_collection(self) -> Collection:
        if self._collection is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(self._persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    @staticmethod
    def _to_metadata(chunk: Chunk) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "repo": chunk.repo,
            "path": chunk.path,
            "kind": chunk.kind,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
        }
        for field in _OPTIONAL_STR_FIELDS:
            value = getattr(chunk, field)
            if value is not None:
                metadata[field] = value
        return metadata

    @staticmethod
    def _from_result(chunk_id: str, document: str, metadata: Mapping[str, Any]) -> Chunk:
        kind: Kind = "code" if metadata.get("kind") == "code" else "doc"
        return Chunk(
            id=chunk_id,
            repo=str(metadata["repo"]),
            path=str(metadata["path"]),
            language=_opt_str(metadata.get("language")),
            kind=kind,
            symbol_name=_opt_str(metadata.get("symbol_name")),
            start_line=int(metadata["start_line"]),
            end_line=int(metadata["end_line"]),
            content=document,
            summary=_opt_str(metadata.get("summary")),
            commit_hash=_opt_str(metadata.get("commit_hash")),
        )

    def upsert(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None:
        if not chunks:
            return
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        collection = self._get_collection()
        collection.upsert(
            ids=[chunk.id for chunk in chunks],
            embeddings=cast("Any", [list(vector) for vector in vectors]),
            documents=[chunk.content for chunk in chunks],
            metadatas=[self._to_metadata(chunk) for chunk in chunks],
        )

    def search(
        self,
        query_vector: Sequence[float],
        k: int,
        filters: Mapping[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        collection = self._get_collection()
        if collection.count() == 0:
            return []
        result = collection.query(
            query_embeddings=cast("Any", [list(query_vector)]),
            n_results=k,
            where=cast("Any", dict(filters)) if filters else None,
        )
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        retrieved: list[RetrievedChunk] = []
        for chunk_id, document, metadata, distance in zip(
            ids, documents, metadatas, distances, strict=True
        ):
            chunk = self._from_result(chunk_id, document or "", metadata or {})
            # Cosine distance in [0, 2] -> similarity score in [-1, 1].
            retrieved.append(RetrievedChunk(chunk=chunk, score=1.0 - float(distance)))
        return retrieved

    def count(self) -> int:
        """Total number of indexed chunks."""
        return self._get_collection().count()

    def file_infos(self, path_query: str | None = None) -> list[FileInfo]:
        """Aggregate indexed chunks into per-file records for ``GET /files``."""
        collection = self._get_collection()
        if collection.count() == 0:
            return []
        result = collection.get(include=["metadatas"])
        metadatas = result.get("metadatas") or []
        by_file: dict[tuple[str, str], FileInfo] = {}
        for metadata in metadatas:
            if metadata is None:
                continue
            repo = str(metadata["repo"])
            path = str(metadata["path"])
            if path_query and path_query.lower() not in path.lower():
                continue
            key = (repo, path)
            existing = by_file.get(key)
            if existing is None:
                kind: Kind = "code" if metadata.get("kind") == "code" else "doc"
                by_file[key] = FileInfo(
                    repo=repo,
                    path=path,
                    kind=kind,
                    language=_opt_str(metadata.get("language")),
                    chunk_count=1,
                )
            else:
                existing.chunk_count += 1
        return sorted(by_file.values(), key=lambda info: (info.repo, info.path))


def _opt_str(value: Any) -> str | None:
    """Coerce an optional metadata value to ``str | None``."""
    if value is None:
        return None
    return str(value)
