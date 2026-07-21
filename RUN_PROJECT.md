
# Run CodeAtlas Locally

This guide starts the current project locally without Docker.

## 1. Prerequisites

Install these first:

- Python 3.12
- `uv`
- Node 22
- `pnpm`

The repo pins Python in `.python-version` and Node in `.nvmrc`.

## 2. Install Python Dependencies

From the repository root:

```bash
uv sync
```

This creates and uses the single shared `.venv/` at the repo root.

## 3. Install Frontend Dependencies

From `frontend/`:

```bash
pnpm install --frozen-lockfile
```

On Windows PowerShell, if `pnpm` is blocked by execution policy, use:

```powershell
pnpm.cmd install --frozen-lockfile
```

## 4. Configure Environment

Copy the template:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` and add your API key:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

The template is already configured for a low-budget setup:

```env
OPENAI_MODEL=gpt-5-nano
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_ENRICHMENT_MODEL=gpt-5-nano
ENABLE_INDEX_SUMMARIES=false
ENABLE_QUERY_EXPANSION=false
ENABLE_LLM_RERANK=false
RETRIEVAL_TOP_K=5
RETRIEVAL_CANDIDATE_K=8
RESET_INDEX_ON_START=false
```

Keep those optional flags disabled if you only have a small API balance.

Set `RESET_INDEX_ON_START=true` if you want the local Chroma index, BM25 index,
and status file wiped every time the backend starts. Leave it `false` if you
want indexed repositories to survive restarts.

## 5. Start The Backend

From the repository root:

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend should be available at:

```text
http://127.0.0.1:8000
```

Check health:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## 6. Start The Frontend

In a second terminal, from `frontend/`:

```bash
pnpm dev
```

On Windows PowerShell:

```powershell
pnpm.cmd dev
```

Open:

```text
http://localhost:3000
```

## 7. Index A Repository

In the web app:

1. Open the `Index` tab.
2. Enter the folder path you want to index.
3. Enter a repo label, for example `my-project`.
4. Click `Start indexing`.
5. Wait for the status to become `completed`.

For a small API budget, start with a small repository or a small folder inside a repository.

If `RESET_INDEX_ON_START=true`, the indexed files list will be empty after every backend restart.
Index the repository again before using chat.

The first index after this update also creates `data/file_manifest.json`, which makes
the Files list and source-preview clicks much faster than scanning the vector database.

The ingester indexes common code and document files, including:

- Code: `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.java`, `.go`, `.rs`, `.rb`, `.c`,
  `.cpp`, `.cs`, `.php`, `.swift`, `.kt`, `.scala`, `.sh`, `.sql`, `.css`,
  `.html`, `.json`, `.yaml`, `.yml`, `.toml`, and similar source/config files.
- Documents: `.md`, `.markdown`, `.mdx`, `.rst`, `.txt`, `.csv`, `.tsv`,
  `.ipynb`, `.pdf`, `.docx`.
- Unknown extensions are attempted as UTF-8 text so project-specific formats can
  still be indexed.

Obvious binary/media/archive files such as images, videos, databases, logs,
compiled artifacts, and zip/tar archives are skipped.

## 8. Chat With The Codebase

After indexing completes:

1. Open the `Chat` tab.
2. Ask a question about the indexed code.
3. The answer should stream back with source file paths and line ranges.
4. Click a source to open the file preview.

## 9. Run Tests

Backend tests from the repository root:

```bash
uv run pytest
```

Frontend tests from `frontend/`:

```bash
pnpm test
```

On Windows PowerShell:

```powershell
pnpm.cmd test
```

## 10. Useful URLs

- Backend health: `http://127.0.0.1:8000/health`
- Backend API docs: `http://127.0.0.1:8000/docs`
- Frontend app: `http://localhost:3000`

## Notes

- Do not commit `.env`; it contains secrets and is git-ignored.
- Paths stored in the index are relative to the indexed repo root.
- For faster answers on a small OpenAI balance, keep `RETRIEVAL_TOP_K=5` and
  `RETRIEVAL_CANDIDATE_K=8`. Increase them only when answers need more source
  context and you accept slower responses.
- Docker is not the recommended path yet because the current compose file is still a scaffold and references Dockerfiles that are not present.
