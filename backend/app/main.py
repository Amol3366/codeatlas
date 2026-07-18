"""FastAPI application and HTTP routes (CLAUDE.md §6).

Exposes the stable API contract the frontends depend on: /health, /ingest,
/status, /files, and the streaming /chat endpoint. The app is a standalone
service and knows nothing about which frontend is calling it (CLAUDE.md §2).
"""

from __future__ import annotations

import json
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
    infos = get_services().vector_store.file_infos(query)
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
    services = get_services()
    infos = [info for info in services.vector_store.file_infos() if info.path == path]
    if not infos:
        raise HTTPException(status_code=404, detail=f"Not an indexed file: {path}")
    info = infos[0]

    last_index = services.status.snapshot().last_successful_index
    if last_index is None:
        raise HTTPException(status_code=409, detail="No successful index recorded yet")

    root = Path(last_index.path).resolve()
    abs_path = (root / path).resolve()
    if root not in abs_path.parents and abs_path != root:
        raise HTTPException(status_code=400, detail="Path escapes the indexed repo root")
    if not abs_path.is_file():
        raise HTTPException(status_code=404, detail=f"File no longer exists on disk: {path}")

    try:
        content = abs_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not read file: {exc}") from exc

    return FileContentResponse(
        repo=info.repo,
        path=path,
        language=info.language,
        content=content,
        total_lines=content.count("\n") + 1,
    )


@app.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Stream a grounded answer via SSE, then emit the final answer + sources."""
    answer_service = AnswerService(get_services())

    async def event_stream() -> AsyncIterator[str]:
        try:
            chunks = await answer_service.retrieve(request.question)
            tokens: list[str] = []
            async for token in answer_service.stream_tokens(
                request.question, chunks, request.history
            ):
                tokens.append(token)
                yield _sse({"type": "token", "value": token})
            sources = answer_service.to_sources(chunks)
            yield _sse(
                {
                    "type": "final",
                    "answer": "".join(tokens),
                    "sources": [source.model_dump() for source in sources],
                }
            )
        except Exception as exc:  # noqa: BLE001 - surface any failure to the client
            yield _sse({"type": "error", "message": f"{type(exc).__name__}: {exc}"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
