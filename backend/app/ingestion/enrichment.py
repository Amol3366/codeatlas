"""Optional index-time enrichment (CLAUDE.md §3, §4 — ``ENABLE_INDEX_SUMMARIES``).

For each chunk, ask the LLM for a one-to-two sentence description of what it
does and store it as ``summary`` so it can be embedded alongside the raw content
to lift semantic recall. Best-effort: a failed summary leaves the chunk's
content intact rather than failing the whole index.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from app.interfaces import LLMClient
from app.models import Chunk

logger = logging.getLogger(__name__)

_MAX_CONTENT_CHARS = 4000


def _build_prompt(chunk: Chunk) -> str:
    kind = "code" if chunk.kind == "code" else "documentation"
    location = chunk.path
    if chunk.symbol_name:
        location = f"{location} ({chunk.symbol_name})"
    content = chunk.content[:_MAX_CONTENT_CHARS]
    return (
        f"Describe, in one or two sentences, what the following {kind} from "
        f"{location} does. Be concrete and specific; do not add commentary.\n\n"
        f"{content}"
    )


def summarize_chunks(chunks: Sequence[Chunk], llm: LLMClient, model: str) -> None:
    """Populate ``chunk.summary`` in place for each chunk (best-effort)."""
    for chunk in chunks:
        try:
            summary = llm.complete(_build_prompt(chunk), model=model).strip()
        except Exception as exc:  # noqa: BLE001 - enrichment is best-effort
            logger.warning("Enrichment failed for %s:%d: %s", chunk.path, chunk.start_line, exc)
            continue
        if summary:
            chunk.summary = summary
