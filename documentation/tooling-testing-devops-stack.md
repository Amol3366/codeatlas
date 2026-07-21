# Tooling, Testing, and DevOps Stack

CodeAtlas uses pinned runtimes and separate package managers for Python and
JavaScript. The goal is reproducibility: everyone should run the same Python,
Node, and dependency versions.

## uv Workspace

The root `pyproject.toml` defines a uv workspace with `backend` and
`prototype-gradio` members. The root `uv.lock` is the single Python lockfile.

Why we use it:

- It creates one shared `.venv` at the repository root.
- It keeps backend and prototype dependencies on one locked set of versions.
- It avoids separate Python environments drifting apart.

Need it solves:

- The backend and optional Python frontend share project contracts and should
  not silently use different versions of common packages.

## Root Python Project

The root project depends on `codeatlas-backend` and provides shared development
tooling configuration for Ruff, mypy, and pytest.

Why we use it:

- Common Python tools are configured once.
- Tests can run from the repository root.
- The workspace remains the source of truth for Python dependency resolution.

Need it solves:

- Developers need one consistent place to install, lint, type-check, and test
  Python code.

## Backend Python Package

`backend/pyproject.toml` declares the backend as `codeatlas-backend` and uses
Hatchling to build the package.

Why we use it:

- The backend can be installed as a workspace package.
- The `app` package is explicitly included.
- Runtime dependencies stay close to the service that uses them.

Need it solves:

- The FastAPI application and tests need importable backend modules with clear
  package metadata.

## Optional Gradio Prototype Package

`prototype-gradio` is a uv workspace member with no current runtime
dependencies.

Why we use it:

- It reserves a place for a thin Python prototype UI.
- It can share the same uv environment and lockfile.
- It is intentionally not allowed to reimplement backend logic.

Need it solves:

- The project can experiment with an alternate frontend while keeping FastAPI as
  the source of truth.

## pnpm Frontend Workspace

The frontend has its own `package.json` and `pnpm-lock.yaml`.

Why we use it:

- JavaScript dependencies are managed separately from Python dependencies.
- pnpm lockfiles make frontend installs reproducible.
- The frontend package declares scripts for dev, build, test, lint, typecheck,
  and formatting.

Need it solves:

- Next.js and React tooling require a Node package workflow independent of uv.

## Version Pinning

The project pins:

- Python 3.12 through `.python-version` and Python project metadata.
- Node 22 through `.nvmrc` and `frontend/package.json`.
- pnpm 10.12.4 through `frontend/package.json`.
- Python dependencies through `uv.lock`.
- Frontend dependencies through `frontend/pnpm-lock.yaml`.

Why we use it:

- Runtime and dependency drift causes hard-to-debug failures.
- AI, retrieval, and frontend packages move quickly.
- Pinned versions make local setup and CI more predictable.

Need it solves:

- The same commands should produce the same behavior across machines.

## Environment Configuration

Runtime settings are documented in `.env.example` and loaded from the root
`.env`.

Important settings include:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `OPENAI_ENRICHMENT_MODEL`
- `EMBEDDING_BACKEND`
- `ENABLE_INDEX_SUMMARIES`
- `ENABLE_QUERY_EXPANSION`
- `ENABLE_LLM_RERANK`
- `CHROMA_PERSIST_DIR`
- `DATA_DIR`
- `RESET_INDEX_ON_START`
- `NEXT_PUBLIC_API_BASE_URL`
- `RETRIEVAL_TOP_K`
- `RETRIEVAL_CANDIDATE_K`

Why we use it:

- Secrets should not be committed.
- Model selection and feature flags should not require source edits.
- Data paths should be configurable for different local setups.

Need it solves:

- The same code can run in test, local development, and containerized contexts
  with different settings.

## Docker Compose

`docker-compose.yml` defines a local backend service and a persistent
`codeatlas-data` volume. The frontend service is scaffolded but commented out.

Why we use it:

- It provides a path toward containerized local development.
- It keeps persisted app data separate from the container lifecycle.
- It documents expected service ports and environment file usage.

Need it solves:

- Developers need a repeatable way to run the backend with persistent local
  indexes.

## Backend Tests

Backend tests live under `backend/tests` and are configured from the root
`pyproject.toml`.

Why we use them:

- Ingestion, readers, chunking, embeddings, retrieval, prompt construction,
  services, and API behavior all have meaningful edge cases.
- Fakes can replace live OpenAI clients so tests do not depend on external API
  calls.

Need it solves:

- Retrieval and source-grounding behavior must be stable. Tests protect the core
  product promise.

## Frontend Tests

Frontend tests use Vitest, Testing Library, and jsdom.

Why we use them:

- Component tests can verify chat rendering, source panel behavior, and SSE
  parsing without a browser server.
- jsdom provides a DOM-like environment for React tests.

Need it solves:

- The streaming chat UI has stateful behavior that should be checked before
  shipping changes.

## Linting and Formatting

Python uses Ruff and mypy. The frontend uses ESLint, TypeScript checks, and
Prettier.

Why we use them:

- Ruff catches common Python errors and keeps imports organized.
- mypy strict mode catches interface and typing problems.
- ESLint catches frontend code issues.
- Prettier keeps formatting consistent.

Need it solves:

- A full-stack codebase needs automated quality gates so style and type
  correctness do not rely on manual review alone.

