# CLAUDE.md — CodeAtlas

> Guidance file for the coding agent (Claude Code). Place this at the **repository root**.
> Rename `CodeAtlas` to your final product name via a project-wide find-and-replace before you begin.

---

## 1. What we are building

**CodeAtlas** ingests one or more codebases and code-related documents, indexes them, and lets a
user ask questions in natural language. It answers with a synthesized explanation **and always
returns the exact file paths (and line ranges) the answer came from.**

Think "chat with your codebase": the user asks *"where is auth handled?"* and gets a plain-English
answer plus a list of source files like `src/auth/session.py:42–88`.

**v1 must deliver, end to end:**

1. **Ingestion** — walk a repo/folder, respect `.gitignore`, classify every file (source code vs.
   document), and parse it into retrievable chunks that carry rich metadata (path, language,
   symbol name, start/end line).
2. **Indexing** — embed chunks and store them in a vector database alongside a keyword index.
3. **Retrieval** — hybrid search (semantic + keyword) that reliably surfaces the right code and docs.
4. **Answering** — an LLM (OpenAI) synthesizes a grounded answer that **cites every source path**.
5. **Chat UI** — a Claude-style chat interface with streaming responses and a clickable "Sources"
   panel showing file paths with a code preview.

If a response cannot be grounded in retrieved sources, say so — never invent a path.

---

## 2. Non-negotiable rules (read before writing any code)

These are hard constraints. Do not deviate without the maintainer's explicit approval.

- **One Python version, one Node version, pinned everywhere.** The stated requirement is that
  language versions stay *strictly identical throughout front and back end development*. Python and
  JavaScript can't share a number, so this rule means: pin **exactly one** Python version and
  **exactly one** Node version, and keep each identical across every developer machine, CI runner,
  and Docker image. No version drift, ever. Enforcement is described in §10.
- **Python is the primary language** for all backend, ingestion, indexing, retrieval, and ML work.
- **Frontend may use TypeScript/React (Next.js).** This is the only place non-Python code is allowed.
- **The backend is a standalone service.** It never imports frontend code and knows nothing about
  which frontend is calling it. Both frontends in §7 talk to the same HTTP API.
- **Every answer is grounded.** No claim about the code without a retrieved source path behind it.
- **Never hardcode secrets or model names in source.** Everything configurable lives in env/config.
- **Small, reviewable commits.** One logical change per commit; tests and linters pass before commit.
- **Type everything.** Python is fully type-hinted; TypeScript runs in `strict` mode.

---

## 3. Tech stack (with pinned versions)

> These are the v1 defaults. If you change a version, change it in **one** place and update all the
> lockfiles/config in §10 in the same commit.

### Backend (Python)

| Concern | Choice | Notes |
|---|---|---|
| Language | **Python 3.12** | Pinned. 3.13 is acceptable only if the whole project moves together. |
| Dependency manager | **uv** | Fast, lockfile-based (`uv.lock`). Do not mix with pip/poetry. |
| Web framework | **FastAPI** | Async, typed, auto OpenAPI docs. |
| ASGI server | **uvicorn** | `uvicorn[standard]`. |
| RAG orchestration | **LangChain** | The orchestration framework for v1. Do **not** use LlamaIndex. |
| Code parsing | **tree-sitter** + language grammars | AST-aware chunking of source files. |
| Vector store | **Chroma** | The vector store for v1 — zero-setup, local, persistent. |
| Keyword search | **rank-bm25** | For exact symbol/path matches, run alongside Chroma. |
| Embeddings | **OpenAI embeddings** (default) | Default: `text-embedding-3-small`. Local `sentence-transformers` (`BAAI/bge-*`) is the offline fallback. |
| Local ML runtime | **PyTorch** | Only needed for the *local* embedding fallback. **Not required** when using OpenAI embeddings (the default). |
| LLM client | **openai** (official Python SDK) | Powers answering, embeddings, and optional index/query enrichment. |
| Validation/config | **pydantic** + **pydantic-settings** | All config via typed settings objects. |
| Testing | **pytest** + **pytest-asyncio** | |
| Lint/format/type | **ruff** (lint+format) + **mypy** | |

> **PyTorch note:** you mentioned PyTorch — it enters only through the *local* embedding fallback
> (via `sentence-transformers`). Since v1 defaults to **OpenAI embeddings**, PyTorch is **not**
> required to run the product; it's only pulled in if someone flips embeddings to `local` for
> offline/air-gapped use. Keep the embedding layer behind an interface (§4) so this stays swappable.

### Frontend

| Concern | Choice | Notes |
|---|---|---|
| Language | **TypeScript 5.x**, `strict: true` | |
| Runtime | **Node 22 LTS** | Pinned. Single version across all machines/CI. |
| Package manager | **pnpm** | Lockfile `pnpm-lock.yaml` committed. |
| Framework | **Next.js (App Router)** | Primary frontend — the "substantial product" UI. |
| Styling | **Tailwind CSS** | |
| Streaming | Server-Sent Events (SSE) from the backend | |

An optional **Gradio** frontend (pure Python) is also specified in §7 for rapid prototyping.

### Where OpenAI is used (and where it must NOT be)

v1 leans on the OpenAI API for all **language-model** work, but the *structural* parts of indexing
stay deterministic. Use OpenAI models in these layers:

1. **Answering (core).** Chat/synthesis of the grounded answer via the OpenAI SDK. Streamed.
2. **Embeddings (core).** Both index-time chunk embeddings and query embeddings use OpenAI embeddings
   (`text-embedding-3-small` by default). The *same* embedding model must be used for indexing and
   querying — never mix models in one collection.
3. **Index-time enrichment (optional, feature-flagged).** For each code chunk / doc section, generate
   a short natural-language description of what it does, then embed *that* alongside the raw content.
   This measurably improves semantic recall on "where/how is X done" questions. Off by a flag because
   it adds indexing cost/time; default it **on** for quality, but make it one toggle to disable.
4. **Query transformation (optional, feature-flagged).** For vague questions, use OpenAI to expand the
   query or generate a hypothetical answer (HyDE) before retrieval. Improves recall; adds one cheap
   call per query. Default **off**; enable per-deployment.
5. **LLM reranking (optional, feature-flagged).** Rerank the top-k merged candidates with OpenAI.
   Highest quality, highest cost/latency. Default **off** for v1.

**Do NOT use an LLM for these — keep them deterministic:**

- File walking, `.gitignore` handling, and file classification.
- **tree-sitter parsing and the extraction of file paths, symbol names, and start/end line numbers.**
  Paths and line ranges are ground-truth metadata and must come from the parser, never from a model —
  an LLM would hallucinate line numbers and break the "return exact paths" guarantee.
- Storage in Chroma and the BM25 keyword index.

**Config discipline for all OpenAI use:**

- **Never hardcode model names.** Read them from config: `OPENAI_MODEL` (answering),
  `OPENAI_EMBEDDING_MODEL` (embeddings), `OPENAI_ENRICHMENT_MODEL` (enrichment/rerank — can point at a
  smaller, cheaper model). Confirm current strings at https://platform.openai.com/docs/models
- Keep every OpenAI call **behind an interface** (`LLMClient`, `Embedder`) — nothing outside those
  layers imports the `openai` SDK directly, so the provider stays swappable.
- Enrichment, query transformation, and reranking are each a **single boolean flag** (§11) so cost is
  controllable and the pipeline degrades gracefully to plain hybrid search when they're off.

---

## 4. Architecture

```
                 ┌────────────────────────────────────────────┐
                 │                Frontend                     │
                 │   Next.js chat UI  (or Gradio prototype)    │
                 └───────────────┬────────────────────────────┘
                                 │ HTTP / SSE
                 ┌───────────────▼────────────────────────────┐
                 │              FastAPI backend                │
                 │  /ingest  /status  /chat  /files  /health   │
                 └───┬───────────────┬───────────────┬────────┘
                     │               │               │
             ┌───────▼──────┐ ┌──────▼───────┐ ┌─────▼────────┐
             │  Ingestion   │ │  Retrieval   │ │  Answering   │
             │  pipeline    │ │  (hybrid)    │ │  (OpenAI)    │
             └───────┬──────┘ └──────┬───────┘ └─────┬────────┘
                     │               │               │
              ┌──────▼───────────────▼──────┐  ┌──────▼───────┐
              │   Vector store + BM25 index │  │  OpenAI API  │
              │  (chunks + rich metadata)   │  └──────────────┘
              └─────────────────────────────┘
```

> The **OpenAI API** is shared by three layers: ingestion (embeddings + optional chunk-description
> enrichment), retrieval (optional query transformation / reranking), and answering. tree-sitter
> parsing and path/line extraction inside ingestion stay local and deterministic — no LLM there.

**Design the backend around clean interfaces** so pieces stay swappable:

- `Embedder` — one method, `embed(texts) -> vectors`. Local or hosted behind the same interface.
- `VectorStore` — `upsert(chunks)`, `search(query_vector, k, filters)`.
- `KeywordIndex` — `search(query, k)` for exact symbol/path hits.
- `Chunker` — `chunk(file) -> list[Chunk]`; code path uses tree-sitter, doc path uses text splitting.
- `LLMClient` — `stream_answer(question, context_chunks) -> token stream`.

> **Use LangChain only — do not use LlamaIndex.** Keep LangChain *behind* the interfaces above; do
> not let LangChain types leak across the codebase. That way the RAG framework stays swappable even
> though v1 is committed to LangChain.

### Ingestion pipeline (the core of v1)

1. **Walk** the target path; honor `.gitignore` and a project ignore list (binaries, `node_modules`,
   `.venv`, build artifacts, images, lockfiles unless explicitly wanted).
2. **Classify** each file:
   - *Source code* → detect language by extension.
   - *Document* → `.md`, `.rst`, `.txt`, `.ipynb`, `.pdf`, `.docx`, etc.
3. **Chunk**:
   - **Code:** parse with tree-sitter and chunk at semantic boundaries (functions, classes,
     methods). Never split a function across chunks if avoidable.
   - **Docs:** split by heading, then by a recursive character splitter with overlap.
4. **Attach metadata to every chunk** (this is what makes "return the paths" work):
   `repo`, `path`, `language`, `symbol_name`, `start_line`, `end_line`, `kind` (`code`|`doc`),
   `commit_hash` (if a git repo). See §5. These fields come from tree-sitter/the walker — **never**
   from an LLM.
5. **Enrich (OpenAI, optional — `ENABLE_INDEX_SUMMARIES`).** For each chunk, ask OpenAI for a one- to
   two-sentence description of what it does; store it as `summary` metadata and embed it together with
   the raw content. This lifts semantic recall on intent-based questions. Skip entirely when the flag
   is off — the pipeline still works on raw content alone.
6. **Embed** chunks (OpenAI embeddings by default) and **upsert** into Chroma; add them to the BM25
   keyword index too.
7. **Record status** so `/status` can report progress and the last successful index.

### Retrieval

- **Query transformation (OpenAI, optional — `ENABLE_QUERY_EXPANSION`).** For vague questions,
  expand the query or generate a hypothetical answer (HyDE) with OpenAI before embedding it. Off by
  default; when on it's one cheap call per query.
- Embed the (possibly transformed) query with the **same** OpenAI embedding model used at index time.
- Run **semantic** search (Chroma) and **keyword/BM25** search in parallel, then merge and
  de-duplicate.
- Keyword search matters for code: users search exact symbol names and paths.
- **Reranking (OpenAI, optional — `ENABLE_LLM_RERANK`).** Rerank the merged top-k with OpenAI for
  higher precision. Default off for v1 (cost/latency); enable per-deployment.
- Return the top-k merged chunks *with full metadata* to the answering layer.

### Answering

- Build a prompt containing the user question and the retrieved chunks (each labeled with its path
  and line range).
- Instruct the model to answer **only** from the provided context and to cite the file paths it used.
- Stream the answer; return the answer text **plus a structured `sources` list** (path + line range)
  so the frontend can render the citations panel.

---

## 5. Data model

A `Chunk` is the atomic unit stored and retrieved. Minimum fields:

```python
class Chunk(BaseModel):
    id: str                 # stable hash of repo+path+start_line+end_line
    repo: str               # repo name or ingest label
    path: str               # path RELATIVE to the repo root  ← always relative, never absolute
    language: str | None    # "python", "typescript", ... ; None for prose docs
    kind: Literal["code", "doc"]
    symbol_name: str | None # function/class/section name if known
    start_line: int
    end_line: int
    content: str            # the raw chunk text
    summary: str | None     # OpenAI-generated description, if ENABLE_INDEX_SUMMARIES is on
    commit_hash: str | None
```

- The text sent to the embedder is `content` alone, or `summary + content` when enrichment is on.

- **Paths are always stored relative to the repo root.** Absolute machine paths must never reach the
  index or the UI. Resolve to absolute only at read-time if a preview needs it.
- Chunk `id` must be **deterministic** so re-indexing updates rather than duplicates.

---

## 6. API contract

Keep these stable; the frontends depend on them. FastAPI generates OpenAPI docs at `/docs`.

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/health` | Liveness check. |
| `POST` | `/ingest` | Body: `{ path, repo_label }`. Kicks off (async) indexing. Returns a job id. |
| `GET`  | `/status` | Indexing progress + last successful index summary. |
| `GET`  | `/files`  | List indexed files with counts; supports a `?query=` path filter. |
| `POST` | `/chat`   | Body: `{ question, history? }`. **Streams** the answer via SSE, then emits a final `sources` event. |

**`/chat` response shape** (final structured payload after the token stream):

```json
{
  "answer": "Authentication is handled in the session module...",
  "sources": [
    { "path": "src/auth/session.py", "start_line": 42, "end_line": 88, "symbol_name": "create_session" }
  ]
}
```

---

## 7. Frontend

### 7a. Primary — Next.js chat UI (the substantial product)

Build a Claude-style chat experience:

- A message thread with user/assistant turns and **token-by-token streaming** over SSE.
- Markdown rendering with syntax-highlighted code blocks.
- A **"Sources" panel** beside each assistant answer listing the cited paths; clicking a source
  shows a code preview scrolled to the cited lines.
- An **index management** view: trigger `/ingest`, watch `/status`, browse `/files`.
- Clean, uncluttered layout; keyboard-send; loading and error states handled.

When you build UI, follow the project's frontend design guidance for typography, spacing, and color —
avoid a default/templated look. Do not hardcode the backend URL; read it from an env var
(`NEXT_PUBLIC_API_BASE_URL`).

### 7b. Optional — Gradio prototype (pure Python)

You suggested Gradio, and it's a great fast path. Ship a **thin Gradio app that calls the same
FastAPI backend** (it does not re-implement retrieval). Use it for quick internal validation and
demos. Because the backend is decoupled (§2), the Gradio app and the Next.js app coexist without
conflict. Treat Gradio as prototype-tier and Next.js as the production UI for v1.

---

## 8. Repository layout

Monorepo. The Python side is a **single uv workspace** rooted at `codeatlas/`: one shared
`.venv/` and one `uv.lock` at the repo root, so the Python members (`backend`,
`prototype-gradio`) can never drift onto different dependency versions. `.env` (secrets)
and `.venv/` (the virtual-environment directory) are different things and both live at the
root, side by side — `.env` is never placed inside `.venv/`.

```
codeatlas/
├─ CLAUDE.md
├─ README.md
├─ pyproject.toml             # uv WORKSPACE root: members, dev tools, shared tool config
├─ uv.lock                    # SINGLE lockfile for the whole repo; committed
├─ .venv/                     # SINGLE shared Python env; git-ignored (a directory)
├─ .env                       # project-global secrets; git-ignored (a plain file, NOT in .venv/)
├─ .env.example               # committed placeholder template
├─ .python-version            # pins Python (e.g. 3.12.x) for the whole repo
├─ .nvmrc                     # pins Node (e.g. 22.x)
├─ docker-compose.yml         # backend (+ frontend) for local dev; Chroma persists to a volume
├─ backend/                   # workspace member
│  ├─ pyproject.toml          # requires-python pinned; backend deps here (NO per-member venv/lock)
│  ├─ Dockerfile              # base image pinned to the SAME Python version
│  ├─ app/
│  │  ├─ main.py              # FastAPI app + routes
│  │  ├─ config.py            # pydantic-settings; loads the root-level .env
│  │  ├─ ingestion/           # walk, classify, chunk (tree-sitter), embed
│  │  ├─ retrieval/           # vector + keyword hybrid search
│  │  ├─ answering/           # prompt build + OpenAI streaming
│  │  ├─ stores/              # VectorStore, KeywordIndex implementations
│  │  └─ models.py            # Chunk and API schemas
│  └─ tests/
├─ frontend/                  # Next.js app
│  ├─ package.json            # "engines" pins Node 22; "packageManager" pins pnpm
│  ├─ pnpm-lock.yaml          # committed
│  └─ app/ ...
└─ prototype-gradio/          # optional Gradio app (pure Python, calls the API) — workspace member
   └─ pyproject.toml
```

---

## 9. Coding standards

**Python**
- Full type hints; `mypy` passes with no ignores added casually.
- `ruff` for both lint and format; no unformatted code committed.
- Functions do one thing; prefer pure functions in ingestion/retrieval for testability.
- No bare `except`; log with context; fail loudly during ingestion rather than silently skipping.

**TypeScript**
- `strict: true`; no `any` without a written reason.
- Components small and typed; data fetching isolated from presentation.
- ESLint + Prettier; format on commit.

**General**
- Docstrings/JSDoc on public functions and modules.
- No secrets, tokens, or absolute local paths in code or tests.

---

## 10. Version pinning & environment (enforcing the core rule)

This section operationalizes the non-negotiable in §2.

**Python — pin once, use everywhere:**
- `.python-version` → the exact version (e.g. `3.12`), at the repo root; applies repo-wide.
- Root `pyproject.toml` and `backend/pyproject.toml` → `requires-python = "==3.12.*"`.
- `backend/Dockerfile` → `FROM python:3.12-slim` (same minor).
- A **single `uv.lock` at the repo root** (uv workspace) committed; `uv sync` from the root
  is the only way to install deps. There is exactly one shared `.venv`; no per-member venvs.

**Node — pin once, use everywhere:**
- `.nvmrc` → the exact major (e.g. `22`).
- `frontend/package.json` → `"engines": { "node": "22.x" }` and `"packageManager": "pnpm@<pinned>"`.
- Frontend Dockerfile (if built) → `FROM node:22-slim` (same major).
- `pnpm-lock.yaml` committed.

**CI must fail the build if:**
- The runner's Python or Node version differs from the pinned values.
- A lockfile is out of date (`uv lock --check`, `pnpm install --frozen-lockfile`).
- `ruff`, `mypy`, `pytest`, `eslint`, `tsc`, or the frontend build fail.

**Also add** a `pre-commit` config running ruff + mypy (backend) and lint-staged (frontend), and a
short "environment setup" section in `README.md` telling contributors to use `.python-version` /
`.nvmrc` (via `uv` and `nvm`/`fnm`) so no one runs a different version.

---

## 11. Configuration (env vars)

All via `pydantic-settings`; document each in `README.md`. Never commit real values.

Config is loaded from a **project-global `.env` file at the repo root** (`codeatlas/.env`) by
`pydantic-settings`. It is a plain secrets file that lives beside `.venv/` at the root — it is
never placed inside `.venv/`, and it is not backend-scoped. Rules:
- **`.env` holds real secrets and is git-ignored** — it must never be committed.
- **`.env.example` is committed** at the repo root as a placeholder template; contributors copy it
  to `.env` and fill in their own values (`cp .env.example .env`).
- Add `.env` to `.gitignore` in the first commit.
- The backend's `config.py` points `pydantic-settings` at the repo-root `.env`.

```
OPENAI_API_KEY=           # required
OPENAI_MODEL=             # answering model, e.g. a current GPT-4-class model
OPENAI_EMBEDDING_MODEL=   # e.g. text-embedding-3-small
OPENAI_ENRICHMENT_MODEL=  # cheaper model for summaries/rerank, e.g. a mini GPT model

# Embeddings backend: "openai" (default) or "local" (sentence-transformers, needs PyTorch)
EMBEDDING_BACKEND=        # "openai" | "local"
EMBEDDING_MODEL=          # only used when EMBEDDING_BACKEND=local

# Optional OpenAI-powered stages (cost/latency knobs)
ENABLE_INDEX_SUMMARIES=   # true (default) -> summarize+embed each chunk for better recall
ENABLE_QUERY_EXPANSION=   # false (default) -> expand/HyDE the query before retrieval
ENABLE_LLM_RERANK=        # false (default) -> rerank top-k with OpenAI

# Vector store (Chroma)
CHROMA_PERSIST_DIR=       # on-disk path where the Chroma collection is persisted
DATA_DIR=                 # where the index / local DB lives
NEXT_PUBLIC_API_BASE_URL= # frontend → backend base URL
```

---

## 12. Testing

- **Ingestion:** feed a tiny fixture repo (a handful of `.py` + `.md` files) and assert chunk counts,
  correct **relative** paths, and accurate `start_line`/`end_line`.
- **Retrieval:** given a known corpus, a known query returns the expected file at rank 1.
- **API:** `pytest` + FastAPI `TestClient` for each endpoint; `/chat` returns grounded `sources`.
- **Grounding guard:** a test that asserts the answer's cited paths all exist in the index.
- **Frontend:** component tests for the chat thread and sources panel; a smoke test that a streamed
  answer renders and its sources are clickable.
- Target meaningful coverage on ingestion/retrieval — that's where correctness lives.

---

## 13. Common commands

```bash
# Backend
cd backend
uv sync                                   # install (respects the lock + pinned Python)
uv run uvicorn app.main:app --reload      # dev server
uv run pytest                             # tests
uv run ruff check . && uv run mypy .      # lint + types

# Frontend
cd frontend
pnpm install --frozen-lockfile
pnpm dev
pnpm lint && pnpm build

# Everything (backend + frontend; Chroma runs embedded and persists to disk)
docker compose up
```

---

## 14. Definition of done for v1

v1 is complete when a user can:

1. Point CodeAtlas at a repo/folder and index it (`/ingest`), watching progress via `/status`.
2. Ask a natural-language question in the Next.js chat UI and get a **streamed, grounded answer**.
3. See a **Sources panel** listing exact relative file paths + line ranges, each opening a preview.
4. Trust that no answer invents a path — ungrounded questions are declined gracefully.
5. Run the whole thing locally with a single pinned Python version and a single pinned Node version,
   with `docker compose up`, and green CI.

## 15. Explicitly out of scope for v1 (do not build yet)

- Auth/multi-user accounts, org permissions.
- Real-time re-indexing on file change / git hooks.
- Multi-repo cross-search ranking tuning beyond basic hybrid search.
- Dedicated cross-encoder reranking *models* (the optional OpenAI rerank flag exists but ships
  **off** by default), agentic multi-step retrieval, code execution.
- Cloud deployment/IaC (local + docker-compose is enough for v1).

Ship a solid, grounded, single-repo "chat with your codebase" first. Then iterate.

---

## 16. Working agreement for the coding agent

- Read this whole file before starting. When a decision here is ambiguous, ask the maintainer
  rather than guessing on architecture.
- Build in the order of §4: interfaces → ingestion → retrieval → answering → API → frontend.
- Keep commits small; run linters/types/tests before each commit; keep versions pinned per §10.
- Never introduce a second Python or Node version. Never store absolute paths. Never fabricate a
  source citation.
