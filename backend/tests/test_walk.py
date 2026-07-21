"""Repository walker ignore behavior."""

from __future__ import annotations

from pathlib import Path

from app.ingestion.walk import walk_repo


def test_walk_repo_skips_heavy_generated_directories_and_logs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("print('index me')\n", encoding="utf-8")
    (repo / "data").mkdir()
    (repo / "data" / "scratch.py").write_text("print('skip me')\n", encoding="utf-8")
    (repo / "coverage").mkdir()
    (repo / "coverage" / "report.txt").write_text("skip coverage\n", encoding="utf-8")
    (repo / "debug.log").write_text("skip logs\n", encoding="utf-8")
    (repo / "local.sqlite").write_text("skip database\n", encoding="utf-8")

    paths = {path.relative_to(repo).as_posix() for path in walk_repo(repo)}

    assert paths == {"app.py"}
