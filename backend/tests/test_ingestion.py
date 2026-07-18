"""Ingestion pipeline over a fixture repo: counts, relative paths, lines (§12)."""

from __future__ import annotations

from pathlib import Path

from app.ingestion.pipeline import run_ingestion
from app.services import Services


def test_pipeline_indexes_all_fixture_files(services: Services, repo: Path) -> None:
    run_ingestion(services, str(repo), "test", "job-1")

    snapshot = services.status.snapshot()
    assert snapshot.state == "completed"
    assert snapshot.files_indexed == 3
    assert snapshot.chunks_indexed > 0
    assert snapshot.last_successful_index is not None
    assert snapshot.last_successful_index.files_indexed == 3


def test_pipeline_stores_relative_paths(services: Services, repo: Path) -> None:
    run_ingestion(services, str(repo), "test", "job-2")
    paths = {info.path for info in services.vector_store.file_infos()}
    assert paths == {"auth.py", "math_utils.py", "README.md"}
    # Always relative to the repo root and POSIX-style — never absolute.
    assert all(not path.startswith("/") and "\\" not in path for path in paths)


def test_pipeline_line_numbers_match_source(services: Services, repo: Path) -> None:
    run_ingestion(services, str(repo), "test", "job-3")
    results = services.keyword_index.search("create_session", 10)
    chunk = next(r.chunk for r in results if r.chunk.symbol_name == "create_session")
    source_lines = (repo / "auth.py").read_text(encoding="utf-8").splitlines()
    assert source_lines[chunk.start_line - 1].startswith("def create_session")


def test_pipeline_reports_failure_for_missing_path(services: Services, tmp_path: Path) -> None:
    run_ingestion(services, str(tmp_path / "does-not-exist"), "test", "job-4")
    snapshot = services.status.snapshot()
    assert snapshot.state == "failed"
    assert snapshot.error is not None
