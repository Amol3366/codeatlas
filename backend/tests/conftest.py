"""Shared pytest fixtures: an isolated Services, a fixture repo, and a client."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from app.config import Settings
from app.main import app
from app.services import Services, set_services
from fastapi.testclient import TestClient

from tests.fakes import FakeEmbedder, FakeLLMClient

AUTH_PY = '''"""Authentication module."""

import time


def create_session(user_id):
    """Create a new user session and return its token."""
    token = _make_token(user_id)
    return {"user": user_id, "token": token}


def _make_token(user_id):
    return f"tok-{user_id}-{int(time.time())}"


class SessionManager:
    """Manages active user sessions in memory."""

    def __init__(self):
        self.sessions = {}

    def add(self, session):
        self.sessions[session["token"]] = session
'''

MATH_UTILS_PY = '''"""Small math helpers."""


def add(first, second):
    return first + second


def multiply(first, second):
    return first * second
'''

README_MD = """# Example Project

## Installation

Run the installer to set up the project dependencies.

## Usage

Import the package and call the helpers.
"""


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Isolated settings pointing at a temp data dir; ignores the real .env."""
    data_dir = tmp_path / "data"
    return Settings(
        _env_file=None,
        openai_api_key="",
        data_dir=data_dir,
        chroma_persist_dir=data_dir / "chroma",
        enable_index_summaries=False,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A tiny fixture repo: two Python files and one Markdown doc."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "auth.py").write_text(AUTH_PY, encoding="utf-8")
    (root / "math_utils.py").write_text(MATH_UTILS_PY, encoding="utf-8")
    (root / "README.md").write_text(README_MD, encoding="utf-8")
    return root


@pytest.fixture
def services(settings: Settings) -> Services:
    """A Services container wired with deterministic fakes."""
    return Services(settings, embedder=FakeEmbedder(), llm=FakeLLMClient())


@pytest.fixture
def client(services: Services) -> Iterator[TestClient]:
    """A TestClient whose routes use the injected Services singleton."""
    set_services(services)
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        set_services(None)
