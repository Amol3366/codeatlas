"""Fast file metadata manifest for previews and file listing.

Chroma is optimized for vector search, not for repeatedly scanning all chunk
metadata when the UI opens a source preview. This manifest persists compact
per-file records during ingestion so /files and /files/content can resolve a
relative path in constant time.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Sequence
from pathlib import Path

from app.models import Chunk, FileInfo, SourceFile


class FileManifest:
    """Persistent per-file metadata derived from indexed chunks."""

    def __init__(self, persist_path: Path) -> None:
        self._persist_path = persist_path
        self._lock = threading.Lock()
        self._files: dict[tuple[str, str], FileInfo] = {}
        self._load()

    def _load(self) -> None:
        if not self._persist_path.exists():
            return
        raw = json.loads(self._persist_path.read_text(encoding="utf-8"))
        for item in raw:
            info = FileInfo.model_validate(item)
            self._files[(info.repo, info.path)] = info

    def _persist(self) -> None:
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            info.model_dump()
            for info in sorted(self._files.values(), key=lambda item: (item.repo, item.path))
        ]
        self._persist_path.write_text(json.dumps(payload), encoding="utf-8")

    def upsert_file(
        self, source_file: SourceFile, repo_root: Path, chunks: Sequence[Chunk]
    ) -> None:
        """Insert or update a file record after successful chunking."""
        if not chunks:
            return
        with self._lock:
            self._files[(source_file.repo, source_file.path)] = FileInfo(
                repo=source_file.repo,
                path=source_file.path,
                repo_root=str(repo_root),
                kind=source_file.kind,
                language=source_file.language,
                chunk_count=len(chunks),
            )
            self._persist()

    def file_infos(self, path_query: str | None = None) -> list[FileInfo]:
        """Return indexed files, optionally filtered by relative path."""
        with self._lock:
            infos = list(self._files.values())
        if path_query:
            lowered = path_query.lower()
            infos = [info for info in infos if lowered in info.path.lower()]
        return sorted(infos, key=lambda info: (info.repo, info.path))

    def find_by_path(self, path: str) -> FileInfo | None:
        """Return the first indexed file with the given relative path."""
        with self._lock:
            matches = [info for info in self._files.values() if info.path == path]
        if not matches:
            return None
        return sorted(matches, key=lambda info: info.repo)[0]
