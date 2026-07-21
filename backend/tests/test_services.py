"""Service container startup behavior."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import app.services as services_module
from app.config import Settings
from app.services import Services, set_services

from tests.fakes import FakeEmbedder, FakeLLMClient


def test_services_reset_index_on_start_removes_persisted_index_data(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    chroma_dir = data_dir / "chroma"
    chroma_dir.mkdir(parents=True)
    (chroma_dir / "marker.txt").write_text("old chroma data", encoding="utf-8")
    (data_dir / "bm25_index.json").write_text("[]", encoding="utf-8")
    (data_dir / "file_manifest.json").write_text("[]", encoding="utf-8")
    (data_dir / "status.json").write_text(
        '{"repo_label":"old","path":"repo","files_indexed":1,"chunks_indexed":1,"finished_at":"now"}',
        encoding="utf-8",
    )

    settings = Settings(
        _env_file=None,
        openai_api_key="",
        data_dir=data_dir,
        chroma_persist_dir=chroma_dir,
        reset_index_on_start=True,
    )

    Services(settings, embedder=FakeEmbedder(), llm=FakeLLMClient())

    assert chroma_dir.is_dir()
    assert not (chroma_dir / "marker.txt").exists()
    assert not (data_dir / "bm25_index.json").exists()
    assert not (data_dir / "file_manifest.json").exists()
    assert not (data_dir / "status.json").exists()


def test_reset_index_on_start_allows_missing_index_paths(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    settings = Settings(
        _env_file=None,
        openai_api_key="",
        data_dir=data_dir,
        chroma_persist_dir=data_dir / "chroma",
        reset_index_on_start=True,
    )

    Services(settings, embedder=FakeEmbedder(), llm=FakeLLMClient())

    assert settings.chroma_persist_dir.is_dir()


def test_get_services_initializes_singleton_once(monkeypatch) -> None:
    created: list[object] = []

    class DummyServices:
        def __init__(self) -> None:
            created.append(object())

    monkeypatch.setattr(services_module, "Services", DummyServices)
    set_services(None)
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            services = list(executor.map(lambda _: services_module.get_services(), range(8)))
    finally:
        set_services(None)

    assert len({id(service) for service in services}) == 1
    assert len(created) == 1
