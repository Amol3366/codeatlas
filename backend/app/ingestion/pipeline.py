"""The ingestion pipeline: walk -> classify -> chunk -> enrich -> embed -> store.

Orchestrates the deterministic ingestion steps (CLAUDE.md §4). Runs as a
background job and reports progress through the :class:`StatusTracker`. Fails
loudly (logs with context and records a failed status) rather than silently
skipping errors.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from app.ingestion.enrichment import summarize_chunks
from app.ingestion.readers import read_source_file
from app.ingestion.walk import get_commit_hash, walk_repo
from app.models import Chunk, IndexSummary
from app.services import Services

logger = logging.getLogger(__name__)


def run_ingestion(services: Services, path: str, repo_label: str, job_id: str) -> None:
    """Index every indexable file under ``path`` into the vector + keyword stores."""
    status = services.status
    status.start(job_id, f"Indexing {repo_label}")
    root = Path(path).expanduser().resolve()
    if not root.exists():
        message = f"Path does not exist: {path}"
        logger.error(message)
        status.fail(message)
        return

    settings = services.settings
    commit_hash = get_commit_hash(root)
    files_seen = 0
    files_indexed = 0
    chunks_indexed = 0

    try:
        for abs_path in walk_repo(root):
            files_seen += 1
            source_file = read_source_file(abs_path, root, repo_label, commit_hash)
            if source_file is None:
                continue
            chunks: list[Chunk] = services.chunker.chunk(source_file)
            if not chunks:
                continue
            if settings.enable_index_summaries:
                summarize_chunks(chunks, services.llm, settings.openai_enrichment_model)
            vectors = services.embedder.embed([chunk.embedding_text() for chunk in chunks])
            services.vector_store.upsert(chunks, vectors)
            services.keyword_index.add(chunks)
            files_indexed += 1
            chunks_indexed += len(chunks)
            status.update(
                files_seen=files_seen,
                files_indexed=files_indexed,
                chunks_indexed=chunks_indexed,
            )
    except Exception as exc:
        logger.exception("Ingestion failed for %s", path)
        status.fail(f"{type(exc).__name__}: {exc}")
        return

    summary = IndexSummary(
        repo_label=repo_label,
        path=str(root),
        files_indexed=files_indexed,
        chunks_indexed=chunks_indexed,
        finished_at=datetime.now(UTC).isoformat(),
    )
    status.complete(summary)
    logger.info("Indexed %s: %d files, %d chunks", repo_label, files_indexed, chunks_indexed)
