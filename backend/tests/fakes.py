"""Deterministic fakes so tests exercise the pipeline without live OpenAI calls."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import AsyncIterator, Sequence

from app.interfaces import Embedder, LLMClient
from app.models import ChatMessage, Chunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class FakeEmbedder(Embedder):
    """Hashing bag-of-words embedder: cosine similarity tracks token overlap."""

    def __init__(self, dim: int = 128) -> None:
        self._dim = dim

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self._dim
        for token in _TOKEN_RE.findall(text.lower()):
            bucket = int(hashlib.md5(token.encode()).hexdigest(), 16) % self._dim
            vector[bucket] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]


class FakeLLMClient(LLMClient):
    """Emits deterministic, grounded-looking output referencing the context."""

    def __init__(self) -> None:
        self.complete_calls: list[str] = []

    async def stream_answer(
        self,
        question: str,
        context_chunks: Sequence[Chunk],
        history: Sequence[ChatMessage] | None = None,
    ) -> AsyncIterator[str]:
        if not context_chunks:
            text = "I cannot find this in the provided sources."
        else:
            text = f"Based on {context_chunks[0].path}, here is the answer."
        for word in text.split(" "):
            yield word + " "

    def complete(self, prompt: str, *, model: str | None = None, temperature: float = 0.0) -> str:
        self.complete_calls.append(prompt)
        return "A concise deterministic summary."
