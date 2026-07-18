"""Dependency container wiring the concrete implementations together.

Holds one instance of each interface implementation for the process. Embedder
and LLM client are lazy so the app (and tests with mocks) can start without an
OpenAI key. Swapping a provider means changing only this module.
"""

from __future__ import annotations

from app.config import Settings, get_settings
from app.embeddings import get_embedder
from app.ingestion.chunker import CompositeChunker
from app.interfaces import Chunker, Embedder, KeywordIndex, LLMClient, VectorStore
from app.status import StatusTracker
from app.stores.keyword_index import BM25KeywordIndex
from app.stores.vector_store import ChromaVectorStore


class Services:
    """Process-wide container of interface implementations."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.settings.ensure_dirs()
        self.vector_store: VectorStore = ChromaVectorStore(self.settings.chroma_persist_dir)
        self.keyword_index: KeywordIndex = BM25KeywordIndex(
            self.settings.data_dir / "bm25_index.json"
        )
        self.chunker: Chunker = CompositeChunker()
        self.status = StatusTracker(self.settings.data_dir / "status.json")
        self._embedder: Embedder | None = None
        self._llm: LLMClient | None = None

    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = get_embedder(self.settings)
        return self._embedder

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            from app.answering.llm import get_llm_client

            self._llm = get_llm_client(self.settings)
        return self._llm


_services: Services | None = None


def get_services() -> Services:
    """Return the process-wide :class:`Services` singleton."""
    global _services
    if _services is None:
        _services = Services()
    return _services


def set_services(services: Services | None) -> None:
    """Override the singleton (used by tests to inject fakes)."""
    global _services
    _services = services
