"""File manifest persistence used by fast source previews."""

from __future__ import annotations

from pathlib import Path

from app.models import Chunk, SourceFile
from app.stores.file_manifest import FileManifest


def test_file_manifest_persists_and_filters_file_infos(tmp_path: Path) -> None:
    persist_path = tmp_path / "file_manifest.json"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    source_file = SourceFile(
        repo="test",
        path="src/app.py",
        abs_path=str(repo_root / "src" / "app.py"),
        content="def run():\n    return 'ok'\n",
        language="python",
        kind="code",
    )
    chunks = [
        Chunk(
            id="chunk-1",
            repo="test",
            path="src/app.py",
            language="python",
            kind="code",
            symbol_name="run",
            start_line=1,
            end_line=2,
            content=source_file.content,
        )
    ]

    manifest = FileManifest(persist_path)
    manifest.upsert_file(source_file, repo_root, chunks)

    reloaded = FileManifest(persist_path)
    infos = reloaded.file_infos("app")
    assert len(infos) == 1
    assert infos[0].path == "src/app.py"
    assert infos[0].repo_root == str(repo_root)
    assert infos[0].chunk_count == 1
    assert reloaded.find_by_path("src/app.py") == infos[0]
    assert reloaded.file_infos("missing") == []
