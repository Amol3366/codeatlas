"""Prompt construction for grounded answering (CLAUDE.md §4 "Answering").

The model is instructed to answer ONLY from the provided context and to cite the
file paths it used. Each context chunk is labelled with its path and line range
so citations map back to ground-truth metadata.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.models import ChatMessage, Chunk

SYSTEM_PROMPT = (
    "You are CodeAtlas, an assistant that answers questions about a codebase.\n"
    "Answer ONLY using the numbered context sources provided by the user. "
    "Every claim about the code must be grounded in those sources.\n"
    "Cite the file paths you used inline, e.g. `src/auth/session.py:42-88`.\n"
    "If the context does not contain enough information to answer, say so plainly "
    "and do not invent file paths, symbols, or line numbers."
)


def format_source_label(chunk: Chunk) -> str:
    """Human-readable label for a context chunk, e.g. ``path:12-40 (symbol)``."""
    label = f"{chunk.path}:{chunk.start_line}-{chunk.end_line}"
    if chunk.symbol_name:
        label = f"{label} ({chunk.symbol_name})"
    return label


def build_context_block(context_chunks: Sequence[Chunk]) -> str:
    """Render retrieved chunks into a numbered, labelled context block."""
    if not context_chunks:
        return "(no sources retrieved)"
    parts: list[str] = []
    for index, chunk in enumerate(context_chunks, start=1):
        parts.append(f"[{index}] {format_source_label(chunk)}\n{chunk.content}")
    return "\n\n".join(parts)


def build_answer_messages(
    question: str,
    context_chunks: Sequence[Chunk],
    history: Sequence[ChatMessage] | None = None,
) -> list[dict[str, str]]:
    """Assemble the chat messages for a grounded answer request."""
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend({"role": turn.role, "content": turn.content} for turn in history)
    context_block = build_context_block(context_chunks)
    user_content = (
        f"Context sources:\n{context_block}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the context above and cite the file paths you relied on."
    )
    messages.append({"role": "user", "content": user_content})
    return messages
