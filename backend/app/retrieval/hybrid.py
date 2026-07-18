"""Hybrid retrieval: semantic + keyword search merged with RRF (CLAUDE.md §4).

Runs the Chroma vector search and the BM25 keyword search, fuses the two ranked
lists with Reciprocal Rank Fusion (no score normalization needed), and applies
the optional query-expansion and rerank stages when their flags are enabled.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.models import RetrievedChunk
from app.retrieval.query_transform import expand_query
from app.retrieval.rerank import rerank
from app.services import Services

# Reciprocal Rank Fusion constant; 60 is the value from the original RRF paper.
_RRF_K = 60


def reciprocal_rank_fusion(
    result_lists: Sequence[Sequence[RetrievedChunk]],
    k: int = _RRF_K,
) -> list[RetrievedChunk]:
    """Fuse several ranked lists into one, scoring by ``sum 1/(k + rank)``."""
    fused_scores: dict[str, float] = {}
    chunks: dict[str, RetrievedChunk] = {}
    for results in result_lists:
        for rank, retrieved in enumerate(results):
            chunk_id = retrieved.chunk.id
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
            chunks.setdefault(chunk_id, retrieved)
    ranked_ids = sorted(fused_scores, key=lambda cid: fused_scores[cid], reverse=True)
    return [RetrievedChunk(chunk=chunks[cid].chunk, score=fused_scores[cid]) for cid in ranked_ids]


class HybridRetriever:
    """Semantic + keyword retrieval with optional expansion and reranking."""

    def __init__(self, services: Services) -> None:
        self._services = services

    def retrieve(self, question: str) -> list[RetrievedChunk]:
        """Return the top merged chunks (with metadata) for ``question``.

        Synchronous by design — it performs blocking embedding/LLM calls, so
        callers on the event loop should run it via ``asyncio.to_thread``.
        """
        settings = self._services.settings
        query = question
        if settings.enable_query_expansion:
            query = expand_query(question, self._services.llm)

        query_vector = self._services.embedder.embed_query(query)
        semantic = self._services.vector_store.search(query_vector, settings.retrieval_candidate_k)
        # Keyword search uses the raw question so exact symbols/paths still match.
        keyword = self._services.keyword_index.search(question, settings.retrieval_candidate_k)

        merged = reciprocal_rank_fusion([semantic, keyword])

        if settings.enable_llm_rerank and merged:
            return rerank(question, merged, self._services.llm, settings.retrieval_top_k)
        return merged[: settings.retrieval_top_k]
