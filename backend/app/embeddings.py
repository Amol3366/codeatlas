"""Embedding implementations behind the :class:`Embedder` interface (CLAUDE.md §3).

OpenAI embeddings are the v1 default; a local ``sentence-transformers`` backend
is the offline fallback and only imports PyTorch when actually selected. The
same embedding model must be used for indexing and querying — never mix models
in one collection (CLAUDE.md §3).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.config import Settings
from app.interfaces import Embedder

if TYPE_CHECKING:
    from openai import OpenAI

# Max inputs per OpenAI embeddings request; large corpora are sent in batches.
_OPENAI_BATCH_SIZE = 128
# Keep each embedding request comfortably below the 8192-token per-input limit
# of the small embedding models. This is a character cap rather than token
# counting because the project does not depend on a tokenizer; 8k ASCII chars is
# conservative for code/docs and prevents one huge chunk from failing ingestion.
_MAX_OPENAI_EMBEDDING_CHARS = 8000


def _embedding_input(text: str) -> str:
    """Return text bounded for OpenAI embeddings without mutating stored chunks."""
    return text[:_MAX_OPENAI_EMBEDDING_CHARS]


class OpenAIEmbedder(Embedder):
    """Embeds text with the OpenAI embeddings API."""

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Add it to the repo-root .env to use "
                "the OpenAI embedding backend (or set EMBEDDING_BACKEND=local)."
            )
        self._api_key = api_key
        self._model = model
        self._client: OpenAI | None = None

    def _get_client(self) -> OpenAI:
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        client = self._get_client()
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _OPENAI_BATCH_SIZE):
            batch = [_embedding_input(text) for text in texts[start : start + _OPENAI_BATCH_SIZE]]
            response = client.embeddings.create(model=self._model, input=batch)
            vectors.extend(item.embedding for item in response.data)
        return vectors


class LocalEmbedder(Embedder):
    """Offline embeddings via sentence-transformers (needs the `local` extra)."""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: object | None = None

    def _get_model(self) -> object:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:  # pragma: no cover - depends on optional extra
                raise RuntimeError(
                    "EMBEDDING_BACKEND=local requires the `local` extra. "
                    "Install it with: uv sync --extra local"
                ) from exc
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._get_model()
        # SentenceTransformer.encode returns an ndarray; normalize to lists.
        vectors = model.encode(list(texts), convert_to_numpy=True)  # type: ignore[attr-defined]
        return [row.tolist() for row in vectors]


def get_embedder(settings: Settings) -> Embedder:
    """Construct the configured embedder (CLAUDE.md §11 ``EMBEDDING_BACKEND``)."""
    if settings.embedding_backend == "local":
        return LocalEmbedder(settings.embedding_model)
    return OpenAIEmbedder(settings.openai_api_key, settings.openai_embedding_model)
