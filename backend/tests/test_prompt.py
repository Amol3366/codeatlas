"""Grounded answer prompt behavior."""

from __future__ import annotations

from app.answering.prompt import build_answer_messages
from app.models import Chunk


def test_answer_prompt_states_project_objective_and_code_priority() -> None:
    chunk = Chunk(
        id="code",
        repo="r",
        path="auth.py",
        language="python",
        kind="code",
        symbol_name="create_session",
        start_line=1,
        end_line=3,
        content="def create_session(user_id):\n    return user_id\n",
    )

    messages = build_answer_messages("where is auth handled?", [chunk])
    combined = "\n".join(message["content"] for message in messages)

    assert "goes through codebases and their related documents" in combined
    assert "prioritize code-source evidence over documentation" in combined
    assert "elaborate the implementation details" in combined
