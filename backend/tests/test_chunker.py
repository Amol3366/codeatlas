"""Chunking correctness: symbols, accurate line ranges, relative paths (§12)."""

from __future__ import annotations

from app.ingestion.chunker import CodeChunker, DocChunker
from app.models import SourceFile

from tests.conftest import AUTH_PY, README_MD


def _code_file(content: str, path: str = "auth.py") -> SourceFile:
    return SourceFile(
        repo="test",
        path=path,
        abs_path=f"/abs/{path}",
        content=content,
        language="python",
        kind="code",
    )


def test_code_chunker_extracts_symbols() -> None:
    chunks = CodeChunker().chunk(_code_file(AUTH_PY))
    symbols = {chunk.symbol_name for chunk in chunks if chunk.symbol_name}
    assert {"create_session", "_make_token", "SessionManager", "add"} <= symbols


def test_code_chunker_line_numbers_are_accurate() -> None:
    chunks = CodeChunker().chunk(_code_file(AUTH_PY))
    lines = AUTH_PY.splitlines()
    create_session = next(c for c in chunks if c.symbol_name == "create_session")
    assert lines[create_session.start_line - 1].startswith("def create_session")
    assert create_session.end_line >= create_session.start_line
    # The full function body is kept in one chunk (never split).
    assert 'return {"user": user_id, "token": token}' in create_session.content


def test_code_chunker_paths_are_relative_and_kind_code() -> None:
    chunks = CodeChunker().chunk(_code_file(AUTH_PY))
    assert chunks
    assert all(chunk.kind == "code" for chunk in chunks)
    assert all(not chunk.path.startswith("/") for chunk in chunks)


def test_unsupported_language_falls_back_to_line_windows() -> None:
    content = "key: value\nother: 123\nnested:\n  a: 1\n"
    chunks = CodeChunker().chunk(_code_file(content, path="config.yaml"))
    assert chunks
    assert all(chunk.start_line >= 1 and chunk.end_line >= chunk.start_line for chunk in chunks)


def test_large_semantic_code_chunk_is_split_before_embedding_limit() -> None:
    long_body = "\n".join(f"    value_{index} = '{'x' * 180}'" for index in range(120))
    content = f"def big_function():\n{long_body}\n    return value_119\n"
    chunks = CodeChunker().chunk(_code_file(content))

    big_chunks = [chunk for chunk in chunks if chunk.symbol_name == "big_function"]
    assert len(big_chunks) > 1
    assert all(len(chunk.content) <= 8500 for chunk in big_chunks)


def test_doc_chunker_produces_doc_chunks_with_line_numbers() -> None:
    doc_file = SourceFile(
        repo="test",
        path="README.md",
        abs_path="/abs/README.md",
        content=README_MD,
        language=None,
        kind="doc",
    )
    chunks = DocChunker().chunk(doc_file)
    assert chunks
    total_lines = README_MD.count("\n") + 1
    for chunk in chunks:
        assert chunk.kind == "doc"
        assert chunk.language is None
        assert 1 <= chunk.start_line <= total_lines
        assert chunk.end_line >= chunk.start_line


def test_doc_chunker_disambiguates_repeated_line_ranges() -> None:
    content = " ".join(f"word{index}" for index in range(900))
    doc_file = SourceFile(
        repo="test",
        path="LONG.md",
        abs_path="/abs/LONG.md",
        content=content,
        language=None,
        kind="doc",
    )

    chunks = DocChunker().chunk(doc_file)
    ids = [chunk.id for chunk in chunks]

    assert len(chunks) > 1
    assert all(chunk.start_line == 1 and chunk.end_line == 1 for chunk in chunks)
    assert len(ids) == len(set(ids))
