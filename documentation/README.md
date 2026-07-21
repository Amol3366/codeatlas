# CodeAtlas Documentation

This folder documents the technology stack used in CodeAtlas, why each major
tool exists in the project, and what need it solves.

CodeAtlas is a full-stack application for asking natural-language questions
about codebases and related documents. The backend ingests files, chunks them,
indexes them for retrieval, and streams grounded answers. The frontend provides
a chat interface, source previews, and index-management screens.

## Documentation Map

- [Architecture Overview](./architecture-overview.md): how the backend,
  frontend, ingestion pipeline, retrieval layer, and answer streaming fit
  together.
- [Backend Stack](./backend-stack.md): Python, FastAPI, Pydantic, OpenAI,
  LangChain, Chroma, BM25, Tree-sitter, document readers, and backend tooling.
- [Frontend Stack](./frontend-stack.md): Next.js, React, TypeScript, Tailwind,
  markdown rendering, syntax highlighting, browser storage, and SSE handling.
- [AI, Retrieval, and Data Stack](./ai-retrieval-data-stack.md): embeddings,
  vector search, keyword search, hybrid retrieval, reranking, persisted data,
  and source grounding.
- [Tooling, Testing, and DevOps Stack](./tooling-testing-devops-stack.md):
  uv, pnpm, version pinning, linting, type checking, tests, Docker Compose, and
  environment configuration.

## Project Stack Summary

| Area | Technology | Need It Solves |
| --- | --- | --- |
| Backend API | Python 3.12, FastAPI, Uvicorn | Serves ingestion, status, files, and streaming chat endpoints. |
| Backend models and config | Pydantic, pydantic-settings | Provides typed request/response models and centralized `.env` config. |
| LLM and embeddings | OpenAI SDK, LangChain integrations | Generates embeddings and streamed grounded answers. |
| Retrieval storage | Chroma, rank-bm25, JSON manifests | Stores semantic vectors, exact keyword search data, file metadata, and index status. |
| Code/document ingestion | Tree-sitter, pathspec, pypdf, python-docx, LangChain splitters | Reads, filters, parses, and chunks source files and documents. |
| Frontend | Node 22, pnpm, Next.js, React, TypeScript | Builds the browser chat UI and index-management experience. |
| Frontend rendering | Tailwind CSS, react-markdown, remark-gfm, rehype-highlight, highlight.js | Styles the UI and renders assistant markdown with code highlighting. |
| Testing and quality | pytest, pytest-asyncio, Ruff, mypy, Vitest, Testing Library, ESLint, Prettier | Keeps backend and frontend behavior checked, typed, formatted, and linted. |
| Local operations | uv workspace, Docker Compose, `.env` | Keeps local setup reproducible and separates secrets from source code. |

