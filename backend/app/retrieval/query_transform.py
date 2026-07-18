"""Optional query transformation (CLAUDE.md §4 — ``ENABLE_QUERY_EXPANSION``).

For vague questions, generate a short hypothetical answer (HyDE) with the LLM
and append it to the question before embedding, improving semantic recall.
Best-effort: on any error the original question is used unchanged. Off by
default (one extra cheap call per query when enabled).
"""

from __future__ import annotations

import logging

from app.interfaces import LLMClient

logger = logging.getLogger(__name__)

_HYDE_PROMPT = (
    "Write a short, hypothetical code or documentation snippet that would answer "
    "the following question about a codebase. Keep it under 80 words; output only "
    "the snippet.\n\nQuestion: {question}"
)


def expand_query(question: str, llm: LLMClient) -> str:
    """Return the question augmented with a hypothetical answer (HyDE)."""
    try:
        hypothetical = llm.complete(_HYDE_PROMPT.format(question=question)).strip()
    except Exception as exc:  # noqa: BLE001 - transformation is best-effort
        logger.warning("Query expansion failed; using raw question: %s", exc)
        return question
    if not hypothetical:
        return question
    return f"{question}\n\n{hypothetical}"
