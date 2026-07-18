# CodeAtlas

Chat with your codebase. CodeAtlas ingests one or more codebases and code-related
documents, indexes them, and answers natural-language questions with a synthesized
explanation **plus the exact file paths and line ranges the answer came from**. If an
answer can't be grounded in retrieved sources, CodeAtlas says so — it never invents a path.

See [`CLAUDE.md`](./CLAUDE.md) for the full specification and architecture.

> **Status:** bootstrap. This commit stands up a reproducible, version-pinned environment
> only. Application features (ingestion, retrieval, answering, API routes, UI) land in
> later tasks.

## Repository layout

The Python side is a **single [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/)**
rooted at `codeatlas/`: one shared `.venv/` and one `uv.lock` at the root, so `backend`
and `prototype-gradio` can never drift onto different dependency versions.

```
codeatlas/
├─ CLAUDE.md               # spec / source of truth
├─ README.md
├─ pyproject.toml          # uv workspace root (members, dev tools, shared config)
├─ uv.lock                 # SINGLE lockfile for the whole repo — committed
├─ .venv/                  # SINGLE shared Python env (git-ignored)  ← a directory
├─ .env                    # project-global secrets (git-ignored)    ← a plain file, NOT in .venv/
├─ .env.example            # config template (copy to .env) — committed
├─ .python-version         # pins Python 3.12 (whole repo)
├─ .nvmrc                  # pins Node 22
├─ docker-compose.yml      # local dev stub (Chroma persists to a volume)
├─ backend/                # FastAPI + ingestion/retrieval/answering (workspace member)
│  ├─ pyproject.toml       # backend deps; requires-python = "==3.12.*"
│  └─ app/                 # ingestion/ retrieval/ answering/ stores/
├─ frontend/               # Next.js chat UI (Node 22, pnpm)
└─ prototype-gradio/       # optional pure-Python Gradio prototype (workspace member)
   └─ pyproject.toml
```

> `.env` and `.venv/` are **different things** and live side-by-side at the root — `.env`
> is a plain secrets file, `.venv/` is the virtual-environment directory. `.env` is never
> placed inside `.venv/`.

## Version pinning (non-negotiable — CLAUDE.md §2, §10)

Exactly **one** Python version and **one** Node version, identical across every machine,
CI runner, and Docker image. No drift.

- **Python 3.12** — pinned in `.python-version` (repo-wide), the root and `backend/`
  `pyproject.toml` (`requires-python = "==3.12.*"`), and the backend Dockerfile
  (`python:3.12-slim`). A single root `.venv` is shared by all Python members.
- **Node 22** — pinned in `.nvmrc`, `frontend/package.json` (`engines.node = "22.x"`,
  `packageManager = "pnpm@..."`), and the frontend Dockerfile (`node:22-slim`).

## Environment setup

### Python — one shared env at the repo root (use [`uv`](https://docs.astral.sh/uv/), never pip/poetry)

Run everything from the **repo root** — there is one environment for the whole project:

```bash
uv sync                 # creates ./.venv and installs all members from uv.lock (Python 3.12)
cp .env.example .env    # then fill in your OpenAI key + model names (root-level .env)
```

`uv` reads `.python-version` and will fetch Python 3.12 if needed. `uv run` works from any
subdirectory and always resolves to the single root `.venv`. Verify:

```bash
uv run python --version    # -> Python 3.12.x
```

**Local embedding fallback (optional, offline/air-gapped).** PyTorch and
`sentence-transformers` are an optional extra and are **not** installed by default:

```bash
uv sync --extra local      # only if you set EMBEDDING_BACKEND=local
```

### Frontend (Node — use `pnpm` via `nvm`/`fnm`)

```bash
cd frontend
nvm use                 # or: fnm use   (reads .nvmrc -> Node 22)
pnpm install --frozen-lockfile
```

## Common commands

All Python commands run from the repo root against the shared env:

```bash
# Backend / Python (from repo root)
uv sync                                    # install everything from the lock
uv run uvicorn app.main:app --reload       # dev server (once routes exist)
uv run pytest                              # tests
uv run ruff check . && uv run mypy .       # lint + types

# Frontend
cd frontend
pnpm dev
pnpm lint && pnpm build

# Everything (Chroma runs embedded, persists to a volume)
docker compose up
```

## Configuration

All config is loaded from a **project-global `.env` at the repo root** via
`pydantic-settings`. `.env` is git-ignored and never committed; `.env.example` is the
committed template listing every variable (OpenAI key/models, `EMBEDDING_BACKEND`, the
`ENABLE_*` flags, `CHROMA_PERSIST_DIR`, `DATA_DIR`, `NEXT_PUBLIC_API_BASE_URL`). Never
hardcode secrets or model names in source.
