"""Embedding boundary guards."""

from __future__ import annotations

from app.embeddings import _embedding_input


def test_openai_embedding_input_is_bounded() -> None:
    text = "x" * 20_000
    bounded = _embedding_input(text)

    assert bounded == text[:8000]
    assert len(bounded) == 8000
