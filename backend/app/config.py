"""Typed application configuration (CLAUDE.md §11).

All configuration is loaded from a single project-global ``.env`` at the repo
root via ``pydantic-settings``. Secrets and model names live here — never as
literals scattered through the codebase (CLAUDE.md §2). Every model name is a
default that ``.env`` overrides; confirm current OpenAI model strings at
https://platform.openai.com/docs/models
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# app/ -> backend/ -> repo root. The .env and the persisted data dir live here.
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings, populated from environment / the root ``.env``."""

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- OpenAI ---------------------------------------------------------
    # Empty by default so config loads (and tests run with mocks) without a key;
    # the OpenAI-backed clients raise a clear error if it is missing when used.
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_enrichment_model: str = "gpt-4o-mini"

    # ---- Embeddings backend --------------------------------------------
    embedding_backend: Literal["openai", "local"] = "openai"
    # Only used when embedding_backend == "local" (needs the `local` extra).
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # ---- Optional OpenAI-powered stages (cost/latency knobs) -----------
    enable_index_summaries: bool = True
    enable_query_expansion: bool = False
    enable_llm_rerank: bool = False

    # ---- Vector store (Chroma) & data ----------------------------------
    chroma_persist_dir: Path = REPO_ROOT / "data" / "chroma"
    data_dir: Path = REPO_ROOT / "data"

    # ---- Frontend -> backend -------------------------------------------
    next_public_api_base_url: str = "http://localhost:8000"

    # ---- Retrieval knobs (sensible v1 defaults) ------------------------
    retrieval_top_k: int = 8
    retrieval_candidate_k: int = 20

    def ensure_dirs(self) -> None:
        """Create the on-disk data directories if they do not yet exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_persist_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached :class:`Settings` instance."""
    return Settings()
