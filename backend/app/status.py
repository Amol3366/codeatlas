"""Indexing job status tracking (CLAUDE.md §4 step 7, §6 ``GET /status``).

Holds the state of the current (or most recent) ingestion job and the summary
of the last successful index. The last successful index is persisted to disk so
it survives restarts. Updated from the ingestion background thread, so all
access is guarded by a lock.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from app.models import IndexSummary, StatusResponse


class StatusTracker:
    """Thread-safe holder of ingestion progress and the last good index."""

    def __init__(self, persist_path: Path) -> None:
        self._persist_path = persist_path
        self._lock = threading.Lock()
        self._state = StatusResponse()
        self._load()

    def _load(self) -> None:
        if not self._persist_path.exists():
            return
        raw = json.loads(self._persist_path.read_text(encoding="utf-8"))
        self._state.last_successful_index = IndexSummary.model_validate(raw)

    def _persist(self) -> None:
        if self._state.last_successful_index is None:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._persist_path.write_text(
            self._state.last_successful_index.model_dump_json(), encoding="utf-8"
        )

    def snapshot(self) -> StatusResponse:
        """Return a copy of the current status."""
        with self._lock:
            return self._state.model_copy(deep=True)

    def start(self, job_id: str, message: str) -> None:
        with self._lock:
            self._state = StatusResponse(
                job_id=job_id,
                state="running",
                message=message,
                last_successful_index=self._state.last_successful_index,
            )

    def update(self, *, files_seen: int, files_indexed: int, chunks_indexed: int) -> None:
        with self._lock:
            self._state.files_seen = files_seen
            self._state.files_indexed = files_indexed
            self._state.chunks_indexed = chunks_indexed

    def complete(self, summary: IndexSummary) -> None:
        with self._lock:
            self._state.state = "completed"
            self._state.message = "Indexing completed"
            self._state.files_indexed = summary.files_indexed
            self._state.chunks_indexed = summary.chunks_indexed
            self._state.last_successful_index = summary
            self._persist()

    def fail(self, error: str) -> None:
        with self._lock:
            self._state.state = "failed"
            self._state.error = error
            self._state.message = "Indexing failed"
