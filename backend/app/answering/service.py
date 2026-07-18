"""Answering orchestration (CLAUDE.md §4 "Answering").

Ties retrieval to the LLM: retrieve grounding chunks, stream a grounded answer,
and expose the structured source list (path + line range) for the citations
panel. Retrieval runs off the event loop via ``asyncio.to_thread`` because it
performs blocking embedding/LLM calls.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence

from app.models import ChatMessage, RetrievedChunk, Source
from app.retrieval.hybrid import HybridRetriever
from app.services import Services


class AnswerService:
    """Coordinates hybrid retrieval and grounded, streamed answering."""

    def __init__(self, services: Services) -> None:
        self._services = services
        self._retriever = HybridRetriever(services)

    async def retrieve(self, question: str) -> list[RetrievedChunk]:
        """Retrieve grounding chunks without blocking the event loop."""
        return await asyncio.to_thread(self._retriever.retrieve, question)

    def stream_tokens(
        self,
        question: str,
        chunks: Sequence[RetrievedChunk],
        history: Sequence[ChatMessage] | None = None,
    ) -> AsyncIterator[str]:
        """Stream the grounded answer token-by-token."""
        context = [retrieved.chunk for retrieved in chunks]
        return self._services.llm.stream_answer(question, context, history)

    @staticmethod
    def to_sources(chunks: Sequence[RetrievedChunk]) -> list[Source]:
        """Convert retrieved chunks into the API's structured source list."""
        sources: list[Source] = []
        seen: set[tuple[str, int, int]] = set()
        for retrieved in chunks:
            chunk = retrieved.chunk
            key = (chunk.path, chunk.start_line, chunk.end_line)
            if key in seen:
                continue
            seen.add(key)
            sources.append(
                Source(
                    path=chunk.path,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    symbol_name=chunk.symbol_name,
                )
            )
        return sources
