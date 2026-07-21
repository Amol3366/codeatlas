# Architecture Overview

CodeAtlas is built as a local-first, full-stack retrieval-augmented generation
application. Its main goal is to answer questions about codebases and
code-related documents with source-grounded citations instead of free-form
answers that cannot be verified.

## High-Level Shape

The project has three main parts:

- `backend/`: a FastAPI service that owns ingestion, indexing, retrieval, and
  answer generation.
- `frontend/`: a Next.js application that provides the chat UI, source preview,
  and index-management screens.
- `data/`: local persisted runtime data such as the Chroma vector collection,
  BM25 keyword corpus, file manifest, and status files.

The root of the repository also owns shared environment and tooling files:

- `pyproject.toml` and `uv.lock` define one Python workspace.
- `.python-version` pins Python 3.12.
- `.nvmrc` and `frontend/package.json` pin Node 22 and pnpm.
- `.env.example` documents runtime configuration.
- `docker-compose.yml` provides a local service definition.

## Request Flow

1. A user enters a question in the frontend chat UI.
2. The frontend sends a `POST /chat` request to the backend.
3. The backend retrieves relevant chunks from both semantic and keyword indexes.
4. The backend builds a grounded prompt using the retrieved chunks.
5. The OpenAI-backed LLM client streams answer tokens.
6. The backend emits Server-Sent Events with token updates and a final payload.
7. The frontend renders the streamed answer and links citations to source
   preview data.

This architecture keeps the user experience responsive because the frontend
does not wait for the whole answer before showing progress.

## Ingestion Flow

1. The frontend or API caller sends `POST /ingest` with a repository or folder
   path and label.
2. The backend walks the target path and filters files using project rules.
3. Supported files are read into normalized `SourceFile` models.
4. Code files are split with Tree-sitter where possible.
5. Documents are split with LangChain text splitters.
6. Chunks are embedded using the configured embedding backend.
7. Chunk vectors are stored in Chroma.
8. Chunk text, paths, and symbols are also added to a BM25 keyword index.
9. File metadata and status are persisted under `data/`.

The need for this pipeline is accuracy. Code questions often depend on exact
symbols, file paths, and line ranges, so the system stores both semantic meaning
and literal source metadata.

## Why Backend and Frontend Are Separate

The backend is responsible for trusted filesystem access, indexing, model calls,
and source-grounded answer construction. The frontend is responsible for the
browser experience only.

This separation is useful because:

- The backend can be tested independently from the UI.
- The frontend can evolve without changing retrieval internals.
- Model provider changes stay behind backend interfaces.
- A second frontend, such as the optional Gradio prototype, can call the same
  FastAPI service.

## Why The Project Uses Retrieval-Augmented Generation

The model should not answer from memory when the user asks about a local
codebase. Retrieval-augmented generation lets the backend select relevant source
chunks first, then ask the model to answer using those chunks.

This is needed because:

- Local code is not part of the model's training data.
- File paths and line ranges must be grounded in the indexed repo.
- Exact symbols and implementation details change frequently.
- The app should say when an answer cannot be grounded.

## API Surface

The backend exposes these core routes:

- `GET /health`: liveness check.
- `POST /ingest`: starts indexing for a folder or repository.
- `GET /status`: returns indexing progress and last successful index data.
- `GET /files`: lists indexed files with chunk counts.
- `GET /files/content`: returns raw content for one indexed file.
- `POST /chat`: streams a grounded answer using SSE.

The frontend depends on this contract through `frontend/lib/api.ts` and
`frontend/lib/sse.ts`.

