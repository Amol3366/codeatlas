"""Optional LLM reranking (CLAUDE.md §4 — ``ENABLE_LLM_RERANK``).

Reranks the merged top-k candidates with the LLM for higher precision. Highest
quality, highest cost/latency, so it is off by default for v1. Best-effort: on
any error the input order is preserved.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence

from app.answering.prompt import format_source_label
from app.interfaces import LLMClient
from app.models import RetrievedChunk

logger = logging.getLogger(__name__)

_MAX_SNIPPET_CHARS = 500


def _build_prompt(question: str, candidates: Sequence[RetrievedChunk]) -> str:
    blocks: list[str] = []
    for index, candidate in enumerate(candidates):
        chunk = candidate.chunk
        snippet = chunk.content[:_MAX_SNIPPET_CHARS]
        blocks.append(f"[{index}] {format_source_label(chunk)}\n{snippet}")
    listing = "\n\n".join(blocks)
    return (
        "Rank the following candidate sources by how well they help answer the "
        "question. Return ONLY a comma-separated list of the candidate numbers, "
        "most relevant first.\n\n"
        f"Question: {question}\n\nCandidates:\n{listing}"
    )


def rerank(
    question: str,
    candidates: Sequence[RetrievedChunk],
    llm: LLMClient,
    top_k: int,
) -> list[RetrievedChunk]:
    """Reorder ``candidates`` by LLM-judged relevance, keeping the top ``top_k``."""
    if len(candidates) <= 1:
        return list(candidates[:top_k])
    try:
        response = llm.complete(_build_prompt(question, candidates))
    except Exception as exc:  # noqa: BLE001 - reranking is best-effort
        logger.warning("Rerank failed; keeping fused order: %s", exc)
        return list(candidates[:top_k])

    order = [int(match) for match in re.findall(r"\d+", response)]
    seen: set[int] = set()
    ranked: list[RetrievedChunk] = []
    for index in order:
        if 0 <= index < len(candidates) and index not in seen:
            seen.add(index)
            ranked.append(candidates[index])
    # Append any candidates the model omitted, preserving their fused order.
    for index, candidate in enumerate(candidates):
        if index not in seen:
            ranked.append(candidate)
    return ranked[:top_k]
