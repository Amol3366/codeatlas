# Backend Stack

The backend is a Python service responsible for ingestion, indexing, retrieval,
answer generation, and source serving. It lives under `backend/` and is managed
as part of the root uv workspace.

## Python 3.12

Python 3.12 is the single backend runtime version. It is pinned in
`.python-version`, the root `pyproject.toml`, and `backend/pyproject.toml`.

Why we use it:

- It is a current, stable Python runtime with strong async support.
- It supports modern typing syntax used across the backend.
- Pinning one version prevents local, CI, and Docker environments from drifting.

Need it solves:

- The backend depends on typed service interfaces, async streaming, Pydantic
  models, and a modern package ecosystem.

## FastAPI

FastAPI is the HTTP API framework used in `backend/app/main.py`.

Why we use it:

- It integrates naturally with Pydantic request and response models.
- It supports async endpoints and streaming responses.
- It provides a concise route layer for `/health`, `/ingest`, `/status`,
  `/files`, `/files/content`, and `/chat`.

Need it solves:

- CodeAtlas needs a clean API boundary between browser UI and retrieval logic.
- The `/chat` endpoint needs to stream Server-Sent Events while the answer is
  generated.

## Uvicorn

Uvicorn is the ASGI server used to run FastAPI locally and in service contexts.

Why we use it:

- It is the standard lightweight server for FastAPI applications.
- It supports async request handling and streaming responses.

Need it solves:

- The app needs a development and runtime server for the backend API.

## Pydantic

Pydantic is used for typed data models in the backend. Request bodies,
responses, chunks, retrieved sources, chat messages, file information, and
status snapshots are represented as structured models.

Why we use it:

- It validates API inputs and outputs.
- It gives the backend one shared schema language.
- It makes tests and service code less error-prone.

Need it solves:

- Retrieval and answering pass around rich metadata such as repo, path, line
  range, symbol name, kind, score, and content. Pydantic keeps that data
  explicit and validated.

## pydantic-settings

`pydantic-settings` loads runtime configuration from the root `.env` file in
`backend/app/config.py`.

Why we use it:

- Secrets, model names, feature flags, data paths, and retrieval knobs stay out
  of source code.
- Environment values are converted into typed settings.
- Tests can override settings cleanly.

Need it solves:

- CodeAtlas must switch between OpenAI and local embedding backends, enable or
  disable optional model-powered stages, and control data locations without code
  edits.

## OpenAI SDK

The OpenAI Python SDK is used for embeddings and streamed chat completions.
Backend imports are intentionally isolated in `backend/app/embeddings.py` and
`backend/app/answering/llm.py`.

Why we use it:

- It provides direct access to OpenAI embedding models.
- It supports streaming chat completions for responsive answers.
- It keeps the model-provider integration explicit and testable.

Need it solves:

- The product needs high-quality embeddings for semantic code search and a
  language model that can synthesize readable, source-grounded answers.

## LangChain Packages

The backend uses selected LangChain packages, mainly for text splitting and
provider integrations:

- `langchain`
- `langchain-openai`
- `langchain-chroma`
- `langchain-community`
- `langchain-text-splitters` through the LangChain package set

Why we use it:

- LangChain provides mature document splitting utilities.
- Markdown and general text splitting are delegated to a known library.
- The project can use LangChain integrations without letting LangChain types
  leak through the whole codebase.

Need it solves:

- Document files are not structured like source code. Recursive text splitting
  creates bounded chunks with overlap, which improves retrieval quality.

## ChromaDB

ChromaDB is the persistent vector store used by
`backend/app/stores/vector_store.py`.

Why we use it:

- It runs locally with low setup overhead.
- It persists vectors under `data/chroma`.
- It supports cosine similarity search for embedded chunks.

Need it solves:

- The app needs semantic retrieval over code and documents. Chroma stores the
  embeddings and returns the nearest chunks for a question.

## rank-bm25

`rank-bm25` powers the keyword index in
`backend/app/stores/keyword_index.py`.

Why we use it:

- Semantic search can miss exact identifiers, paths, and API names.
- BM25 is simple, fast, and effective for lexical matching.
- The project persists the corpus as JSON and rebuilds BM25 lazily.

Need it solves:

- Code questions often mention exact names like functions, classes, endpoints,
  files, or errors. Keyword search catches those exact matches.

## Tree-sitter and tree-sitter-language-pack

Tree-sitter parses code so chunks can follow semantic boundaries such as
functions, classes, methods, interfaces, structs, and enums.

Why we use it:

- Code should not be split randomly when a parser can identify useful units.
- Tree-sitter supports many languages through parser packs.
- The backend can fall back to line windows when no parser is available.

Need it solves:

- Retrieval is better when chunks map to real code structures. A whole function
  or method is usually more useful than an arbitrary slice of text.

## pathspec

`pathspec` is used for path filtering patterns while walking repositories.

Why we use it:

- Repositories contain generated files, build outputs, dependency folders, and
  ignored content.
- Git-style ignore rules are familiar and expressive.

Need it solves:

- Ingestion should focus on useful source and documentation files, not noisy
  folders such as dependency caches or build artifacts.

## pypdf and python-docx

`pypdf` reads PDF text and `python-docx` reads DOCX content.

Why we use them:

- CodeAtlas indexes code-related documents as well as source files.
- PDF and DOCX need dedicated parsers instead of plain text readers.

Need it solves:

- Architecture notes, requirements, API docs, and specs may live outside source
  files. These readers let the retrieval system include that context.

## Optional Local Embeddings

The optional `local` extra installs `sentence-transformers` and `torch`.

Why we use it:

- Some environments need offline or air-gapped embedding support.
- It avoids forcing heavy PyTorch dependencies into the default install.

Need it solves:

- Teams can run indexing without OpenAI embedding calls when configured with
  `EMBEDDING_BACKEND=local`.

## Backend Quality Tools

The backend uses:

- `pytest` for tests.
- `pytest-asyncio` for async test support.
- `ruff` for linting and import/style checks.
- `mypy` in strict mode for static typing.
- `hatchling` as the backend package build backend.

Why we use them:

- The backend has retrieval, indexing, model, and filesystem behavior that needs
  regression coverage.
- Strict typing catches interface mistakes before runtime.
- Linting keeps code consistent across modules.

