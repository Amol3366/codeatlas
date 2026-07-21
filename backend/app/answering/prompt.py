"""Prompt construction for grounded answering (CLAUDE.md §4 "Answering").

The model is instructed to answer ONLY from the provided context and cite with
short markdown links. Each context chunk is labelled with its path and line
range so citations map back to ground-truth metadata.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.models import ChatMessage, Chunk

SYSTEM_PROMPT = (
    "You are codeAtlas, an assistant that goes through codebases and their "
    "related documents so users can understand how a project works.\n"
    "Answer ONLY using the numbered context sources provided by the user. "
    "Every claim about the code must be grounded in those sources.\n"
    "When the user asks about code, implementation, functions, classes, APIs, "
    "errors, configuration, or a coding file, prioritize code-source evidence "
    "over documentation when code sources are available. Explain what the "
    "relevant code does, how it fits into the flow, and mention important "
    "symbols or line ranges from the cited sources.\n"
    "Use project documents as supporting context when they clarify purpose, "
    "setup, architecture, or usage.\n"
    "Do not write raw file paths in the answer body. Cite sources by turning one "
    "short word into a markdown link, e.g. `[here](#source-1)`, where the number "
    "matches the source number in the context.\n"
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
        "Answer using only the context above. When citing, use markdown links "
        "like `[here](#source-1)` or link one important word to the relevant "
        "source number. For code questions, prefer code sources and elaborate "
        "the implementation details before using docs as supporting context. "
        "Do not print raw file paths in the answer body."
    )
    messages.append({"role": "user", "content": user_content})
    return messages
