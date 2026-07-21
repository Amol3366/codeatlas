"""OpenAI LLM request compatibility helpers."""

from __future__ import annotations

from app.answering.llm import _temperature_kwargs


def test_temperature_is_omitted_for_gpt_5_models() -> None:
    assert _temperature_kwargs("gpt-5-nano", 0.0) == {}
    assert _temperature_kwargs("gpt-5-mini", 0.0) == {}


def test_temperature_is_sent_for_non_gpt_5_models() -> None:
    assert _temperature_kwargs("gpt-4o-mini", 0.0) == {"temperature": 0.0}
