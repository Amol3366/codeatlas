"""Abstract interfaces that keep the RAG pieces swappable (CLAUDE.md §4).

The whole backend is designed around these five interfaces. Concrete
implementations live in the ingestion/retrieval/answering/stores packages, so
the embedding provider, vector store, keyword index, chunking strategy, and LLM
provider can each be replaced without touching call sites.

Provider SDKs stay behind these boundaries: only :class:`Embedder` /
:class:`LLMClient` implementations import the ``openai`` SDK, and only the
:class:`Chunker` implementation imports LangChain (CLAUDE.md §3, §4).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Mapping, Sequence

from app.models import ChatMessage, Chunk, FileInfo, RetrievedChunk, SourceFile


class Embedder(ABC):
    """Turns text into vectors. Local or hosted, behind one interface."""

    @abstractmethod
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch of texts, preserving order."""

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string (convenience over :meth:`embed`)."""
        return self.embed([text])[0]


class VectorStore(ABC):
    """Persistent semantic index over chunk embeddings."""

    @abstractmethod
    def upsert(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None:
        """Insert or update ``chunks`` with their pre-computed ``vectors``.

        Embeddings are computed by an :class:`Embedder` in the ingestion layer
        and passed in, keeping this store free of any embedding provider.
        """

    @abstractmethod
    def search(
        self,
        query_vector: Sequence[float],
        k: int,
        filters: Mapping[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        """Return the ``k`` nearest chunks to ``query_vector``."""

    @abstractmethod
    def count(self) -> int:
        """Return the total number of indexed chunks."""

    @abstractmethod
    def file_infos(self, path_query: str | None = None) -> list[FileInfo]:
        """Aggregate indexed chunks into per-file records (``GET /files``)."""


class KeywordIndex(ABC):
    """Exact keyword/symbol/path search (BM25) alongside the vector store."""

    @abstractmethod
    def add(self, chunks: Sequence[Chunk]) -> None:
        """Add chunks to the keyword index."""

    @abstractmethod
    def search(self, query: str, k: int) -> list[RetrievedChunk]:
        """Return the top ``k`` chunks for an exact/keyword ``query``."""


class Chunker(ABC):
    """Splits a file into retrievable chunks with accurate metadata."""

    @abstractmethod
    def chunk(self, file: SourceFile) -> list[Chunk]:
        """Chunk a single file. Code uses tree-sitter; docs use text splitting."""


class LLMClient(ABC):
    """The single boundary for all language-model calls (CLAUDE.md §3, §4)."""

    @abstractmethod
    def stream_answer(
        self,
        question: str,
        context_chunks: Sequence[Chunk],
        history: Sequence[ChatMessage] | None = None,
    ) -> AsyncIterator[str]:
        """Stream a grounded answer token-by-token from the given context."""

    @abstractmethod
    def complete(self, prompt: str, *, model: str | None = None, temperature: float = 0.0) -> str:
        """Return a single non-streamed completion.

        Powers the optional index-time enrichment, query transformation, and
        reranking stages (CLAUDE.md §3).
        """
