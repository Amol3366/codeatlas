"""The OpenAI-backed :class:`LLMClient` (CLAUDE.md §3, §4).

This module is the ONLY place, together with the embedder, that imports the
``openai`` SDK. It powers streamed answering plus the optional non-streamed
completions used by enrichment, query transformation, and reranking.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import TYPE_CHECKING, cast

from app.answering.prompt import build_answer_messages
from app.config import Settings
from app.interfaces import LLMClient
from app.models import ChatMessage, Chunk

if TYPE_CHECKING:
    from openai import AsyncOpenAI, AsyncStream, OpenAI
    from openai.types.chat import ChatCompletionChunk


class OpenAILLMClient(LLMClient):
    """Answering + utility completions via the OpenAI chat completions API."""

    def __init__(self, api_key: str, model: str, enrichment_model: str) -> None:
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Add it to the repo-root .env to use "
                "OpenAI answering/enrichment."
            )
        self._api_key = api_key
        self._model = model
        self._enrichment_model = enrichment_model
        self._sync_client: OpenAI | None = None
        self._async_client: AsyncOpenAI | None = None

    def _get_sync_client(self) -> OpenAI:
        if self._sync_client is None:
            from openai import OpenAI

            self._sync_client = OpenAI(api_key=self._api_key)
        return self._sync_client

    def _get_async_client(self) -> AsyncOpenAI:
        if self._async_client is None:
            from openai import AsyncOpenAI

            self._async_client = AsyncOpenAI(api_key=self._api_key)
        return self._async_client

    async def stream_answer(
        self,
        question: str,
        context_chunks: Sequence[Chunk],
        history: Sequence[ChatMessage] | None = None,
    ) -> AsyncIterator[str]:
        client = self._get_async_client()
        messages = build_answer_messages(question, context_chunks, history)
        stream = await client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            temperature=0.0,
            stream=True,
        )
        stream = cast("AsyncStream[ChatCompletionChunk]", stream)
        async for event in stream:
            if not event.choices:
                continue
            token = event.choices[0].delta.content
            if token:
                yield token

    def complete(self, prompt: str, *, model: str | None = None, temperature: float = 0.0) -> str:
        client = self._get_sync_client()
        response = client.chat.completions.create(
            model=model or self._enrichment_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""


def get_llm_client(settings: Settings) -> OpenAILLMClient:
    """Construct the configured OpenAI LLM client."""
    return OpenAILLMClient(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        enrichment_model=settings.openai_enrichment_model,
    )
