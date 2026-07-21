"""FastAPI application and HTTP routes (CLAUDE.md §6).

Exposes the stable API contract the frontends depend on: /health, /ingest,
/status, /files, and the streaming /chat endpoint. The app is a standalone
service and knows nothing about which frontend is calling it (CLAUDE.md §2).
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.answering.service import AnswerService
from app.ingestion.pipeline import run_ingestion
from app.models import (
    ChatRequest,
    FileContentResponse,
    FilesResponse,
    IngestRequest,
    IngestResponse,
    StatusResponse,
)
from app.services import get_services

app = FastAPI(title="CodeAtlas", version="0.1.0")
logger = logging.getLogger(__name__)

# Local dev CORS. Auth/multi-user is out of scope for v1 (CLAUDE.md §15), so a
# permissive policy is acceptable for a locally-run service.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse(payload: dict[str, object]) -> str:
    """Encode one Server-Sent Event data frame."""
    return f"data: {json.dumps(payload)}\n\n"


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest, background_tasks: BackgroundTasks) -> IngestResponse:
    """Kick off asynchronous indexing of a repo/folder."""
    services = get_services()
    job_id = uuid.uuid4().hex
    background_tasks.add_task(run_ingestion, services, request.path, request.repo_label, job_id)
    return IngestResponse(job_id=job_id, status="started")


@app.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    """Report indexing progress and the last successful index."""
    return get_services().status.snapshot()


@app.get("/files", response_model=FilesResponse)
def files(query: str | None = None) -> FilesResponse:
    """List indexed files with chunk counts, optionally filtered by path."""
    services = get_services()
    manifest_infos = services.file_manifest.file_infos()
    if manifest_infos:
        infos = services.file_manifest.file_infos(query)
    else:
        infos = services.vector_store.file_infos(query)
    return FilesResponse(
        files=infos,
        total_files=len(infos),
        total_chunks=sum(info.chunk_count for info in infos),
    )


@app.get("/files/content", response_model=FileContentResponse)
def file_content(path: str) -> FileContentResponse:
    """Return the raw text of one indexed file for the source preview (§7a).

    Only files present in the index are served; the relative path is resolved
    against the last successful ingest root and traversal outside it is
    rejected. Absolute paths never enter or leave the index (CLAUDE.md §5).
    """
    started = time.perf_counter()
    services = get_services()
    info = services.file_manifest.find_by_path(path)
    if info is None:
        matches = [item for item in services.vector_store.file_infos() if item.path == path]
        if not matches:
            raise HTTPException(status_code=404, detail=f"Not an indexed file: {path}")
        info = sorted(matches, key=lambda item: item.repo)[0]

    root_path = info.repo_root
    if root_path is None:
        last_index = services.status.snapshot().last_successful_index
        root_path = last_index.path if last_index is not None else None
    if root_path is None:
        raise HTTPException(status_code=409, detail="No successful index recorded yet")

    root = Path(root_path).resolve()
    abs_path = (root / path).resolve()
    if root not in abs_path.parents and abs_path != root:
        raise HTTPException(status_code=400, detail="Path escapes the indexed repo root")
    if not abs_path.is_file():
        raise HTTPException(status_code=404, detail=f"File no longer exists on disk: {path}")

    try:
        content = abs_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not read file: {exc}") from exc

    response = FileContentResponse(
        repo=info.repo,
        path=path,
        language=info.language,
        content=content,
        total_lines=content.count("\n") + 1,
    )
    logger.info(
        "file_content path=%s lines=%d elapsed_ms=%.1f",
        path,
        response.total_lines,
        (time.perf_counter() - started) * 1000,
    )
    return response


@app.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Stream a grounded answer via SSE, then emit the final answer + sources."""
    answer_service = AnswerService(get_services())

    async def event_stream() -> AsyncIterator[str]:
        try:
            started = time.perf_counter()
            greeting = answer_service.greeting_response(request.question)
            if greeting is not None:
                yield _sse({"type": "token", "value": greeting})
                yield _sse({"type": "final", "answer": greeting, "sources": []})
                logger.info(
                    "chat greeting elapsed_ms=%.1f",
                    (time.perf_counter() - started) * 1000,
                )
                return

            retrieval_started = time.perf_counter()
            chunks = await answer_service.retrieve(request.question)
            retrieval_ms = (time.perf_counter() - retrieval_started) * 1000
            tokens: list[str] = []
            llm_started = time.perf_counter()
            async for token in answer_service.stream_tokens(
                request.question, chunks, request.history
            ):
                tokens.append(token)
                yield _sse({"type": "token", "value": token})
            llm_ms = (time.perf_counter() - llm_started) * 1000
            sources = answer_service.to_sources(chunks)
            yield _sse(
                {
                    "type": "final",
                    "answer": "".join(tokens),
                    "sources": [source.model_dump() for source in sources],
                }
            )
            logger.info(
                "chat question_chars=%d chunks=%d retrieval_ms=%.1f llm_ms=%.1f total_ms=%.1f",
                len(request.question),
                len(chunks),
                retrieval_ms,
                llm_ms,
                (time.perf_counter() - started) * 1000,
            )
        except Exception as exc:  # noqa: BLE001 - surface any failure to the client
            yield _sse({"type": "error", "message": f"{type(exc).__name__}: {exc}"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
