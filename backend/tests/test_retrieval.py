"""Hybrid retrieval: a known query surfaces the expected file first (§12)."""

from __future__ import annotations

from pathlib import Path

from app.ingestion.pipeline import run_ingestion
from app.models import Chunk, RetrievedChunk
from app.retrieval.hybrid import (
    HybridRetriever,
    looks_like_code_question,
    prioritize_code_sources,
    reciprocal_rank_fusion,
)
from app.services import Services


def test_semantic_query_ranks_expected_file_first(services: Services, repo: Path) -> None:
    run_ingestion(services, str(repo), "test", "job")
    results = HybridRetriever(services).retrieve("how are user sessions created")
    assert results
    assert results[0].chunk.path == "auth.py"


def test_symbol_query_matches_by_keyword(services: Services, repo: Path) -> None:
    run_ingestion(services, str(repo), "test", "job")
    results = HybridRetriever(services).retrieve("multiply")
    assert any(result.chunk.path == "math_utils.py" for result in results)


def test_rrf_fuses_and_rewards_agreement() -> None:
    def chunk(chunk_id: str) -> Chunk:
        return Chunk(
            id=chunk_id,
            repo="r",
            path=f"{chunk_id}.py",
            language="python",
            kind="code",
            symbol_name=None,
            start_line=1,
            end_line=2,
            content="x",
        )

    semantic = [
        RetrievedChunk(chunk=chunk("a"), score=0.9),
        RetrievedChunk(chunk=chunk("b"), score=0.8),
    ]
    keyword = [
        RetrievedChunk(chunk=chunk("b"), score=5.0),
        RetrievedChunk(chunk=chunk("c"), score=1.0),
    ]
    fused = reciprocal_rank_fusion([semantic, keyword])
    # "b" appears in both lists, so it should fuse to the top.
    assert fused[0].chunk.id == "b"
    assert {r.chunk.id for r in fused} == {"a", "b", "c"}


def test_code_questions_prioritize_code_sources_over_docs() -> None:
    doc_chunk = Chunk(
        id="doc",
        repo="r",
        path="README.md",
        language="markdown",
        kind="doc",
        symbol_name=None,
        start_line=1,
        end_line=3,
        content="Authentication overview",
    )
    code_chunk = Chunk(
        id="code",
        repo="r",
        path="auth.py",
        language="python",
        kind="code",
        symbol_name="create_session",
        start_line=10,
        end_line=20,
        content="def create_session(user_id): ...",
    )
    results = [
        RetrievedChunk(chunk=doc_chunk, score=0.99),
        RetrievedChunk(chunk=code_chunk, score=0.01),
    ]

    prioritized = prioritize_code_sources("where is authentication handled?", results)

    assert looks_like_code_question("where is authentication handled?")
    assert prioritized[0].chunk.path == "auth.py"


def test_document_questions_keep_retrieval_score_order() -> None:
    doc_chunk = Chunk(
        id="doc",
        repo="r",
        path="README.md",
        language="markdown",
        kind="doc",
        symbol_name=None,
        start_line=1,
        end_line=3,
        content="Installation instructions",
    )
    code_chunk = Chunk(
        id="code",
        repo="r",
        path="install.py",
        language="python",
        kind="code",
        symbol_name=None,
        start_line=1,
        end_line=2,
        content="print('install')",
    )
    results = [
        RetrievedChunk(chunk=doc_chunk, score=0.99),
        RetrievedChunk(chunk=code_chunk, score=0.01),
    ]

    prioritized = prioritize_code_sources("how do I install this project?", results)

    assert not looks_like_code_question("how do I install this project?")
    assert prioritized == results
