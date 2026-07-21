# AI, Retrieval, and Data Stack

CodeAtlas uses a retrieval-augmented generation stack. The important design
choice is that the model answers using retrieved source chunks instead of
guessing from memory.

## OpenAI Answering Model

The answering model is configured through `OPENAI_MODEL` in the root `.env`.
The backend wraps it in `OpenAILLMClient`.

Why we use it:

- It turns retrieved chunks into a readable explanation.
- It can stream tokens, which improves the chat experience.
- The model name is configurable, so cost and quality can be adjusted without
  source changes.

Need it solves:

- Retrieval finds evidence, but users need a synthesized answer that explains
  what the code does and where the answer came from.

## OpenAI Embedding Model

The default embedding model is configured through `OPENAI_EMBEDDING_MODEL`.
The backend uses it to embed chunks during ingestion and to embed questions at
query time.

Why we use it:

- Embeddings let the system find semantically related chunks even when the
  wording differs.
- The same embedding path is used for indexing and querying.
- It provides a strong default retrieval quality with little local setup.

Need it solves:

- Users may ask conceptual questions rather than exact-symbol questions.
  Semantic search can match intent to relevant code and docs.

## Local Embedding Backend

The optional local backend uses `sentence-transformers` and `torch` when
`EMBEDDING_BACKEND=local`.

Why we use it:

- It supports offline or restricted environments.
- It keeps heavy ML dependencies out of the default installation.

Need it solves:

- Some users need indexing without sending text to an external embedding API.

## Chroma Vector Store

Chroma stores chunk embeddings and metadata in a persistent local collection.

Why we use it:

- It runs without a separate database server.
- It persists data under `data/chroma`.
- It supports nearest-neighbor search over embedding vectors.
- It stores metadata such as repo, path, kind, language, symbol, and line range.

Need it solves:

- CodeAtlas needs to retrieve source chunks by semantic similarity quickly and
  locally.

## BM25 Keyword Index

The BM25 index stores searchable chunk text, paths, symbols, and summaries.

Why we use it:

- Exact identifiers matter in code search.
- BM25 performs strong lexical matching for names and terms.
- The index is persisted as JSON in `DATA_DIR`, then rebuilt in memory as
  needed.

Need it solves:

- A vector search may not rank an exact function name, endpoint, file path, or
  error string as highly as a lexical search would. BM25 fills that gap.

## Hybrid Retrieval

The backend uses hybrid retrieval in `backend/app/retrieval/hybrid.py`.

How it works:

1. Embed the question.
2. Search Chroma for semantic candidates.
3. Search BM25 for keyword candidates.
4. Merge ranked lists with Reciprocal Rank Fusion.
5. Prioritize code chunks for implementation-style questions.
6. Optionally expand the query or rerank results with the LLM when enabled.

Why we use it:

- Semantic search and keyword search solve different parts of code retrieval.
- Reciprocal Rank Fusion combines rankings without fragile score
  normalization.
- Code-specific prioritization improves answers for implementation questions.

Need it solves:

- Users ask both conceptual questions and exact questions. Hybrid retrieval
  handles both better than either search method alone.

## Tree-sitter Code Chunking

Tree-sitter parses code into semantic spans.

Why we use it:

- Functions, classes, methods, and similar structures are meaningful retrieval
  units.
- The chunker can keep a symbol together instead of splitting it arbitrarily.
- Unsupported languages still work through a line-window fallback.

Need it solves:

- Source-grounded answers are more useful when retrieved chunks contain complete
  implementation units.

## LangChain Document Chunking

Document files are split with LangChain recursive text splitters.

Why we use it:

- Documents are prose-heavy and do not have code AST structures.
- Chunk overlap preserves context across boundaries.
- Markdown receives language-aware splitting behavior.

Need it solves:

- Docs, READMEs, requirements, and design notes need to be retrievable alongside
  code without sending huge documents to the model.

## File Readers

The backend reads several content types:

- UTF-8 source and text files.
- Jupyter notebooks by flattening markdown and code cells.
- PDFs through `pypdf`.
- DOCX files through `python-docx`.

Why we use them:

- Project knowledge may live in many file formats.
- Dedicated readers avoid treating binary or structured documents as plain text.

Need it solves:

- CodeAtlas can index both implementation and supporting documentation.

## Source Grounding

Every chunk carries metadata:

- Repository label.
- Relative path.
- File kind.
- Language.
- Symbol name when available.
- Start and end line.
- Optional commit hash.

Why we use it:

- The answer must point back to evidence.
- The frontend needs source metadata to open the preview drawer.
- Relative paths avoid exposing arbitrary absolute paths in answers.

Need it solves:

- The product promise is not just "answer a question"; it is "answer with exact
  file and line evidence."

## Persisted Runtime Data

Runtime data is stored under the configured `DATA_DIR`.

Current persisted data includes:

- `data/chroma`: Chroma vector collection.
- `data/bm25_index.json`: persisted keyword corpus.
- `data/file_manifest.json`: indexed file metadata.
- `data/status.json`: ingest progress and last successful index.

Why we use it:

- Indexing a codebase can be expensive and slow.
- Persisting local data allows the app to restart without losing the index.

Need it solves:

- The project needs repeatable local use without requiring a remote database.

## Optional LLM Stages

The backend has feature flags for optional model-powered stages:

- `ENABLE_INDEX_SUMMARIES`
- `ENABLE_QUERY_EXPANSION`
- `ENABLE_LLM_RERANK`

Why we use them:

- They can improve retrieval quality or context quality.
- They also add cost and latency, so they are configurable.

Need it solves:

- Users can choose a budget-safe default or enable deeper AI processing when it
  is worth the extra model calls.

