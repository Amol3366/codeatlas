"""API endpoint tests, including the grounding guard (§6, §12)."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient


def _parse_sse(text: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for line in text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    return events


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_status_is_idle_before_any_ingest(client: TestClient) -> None:
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json()["state"] == "idle"


def test_ingest_then_status_and_files(client: TestClient, repo: Path) -> None:
    response = client.post("/ingest", json={"path": str(repo), "repo_label": "test"})
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"]
    assert body["status"] == "started"

    # TestClient runs the background ingestion task before returning.
    status = client.get("/status").json()
    assert status["state"] == "completed"
    assert status["files_indexed"] == 3

    files = client.get("/files").json()
    assert files["total_files"] == 3
    assert {item["path"] for item in files["files"]} == {
        "auth.py",
        "math_utils.py",
        "README.md",
    }


def test_files_query_filter(client: TestClient, repo: Path) -> None:
    client.post("/ingest", json={"path": str(repo), "repo_label": "test"})
    files = client.get("/files", params={"query": "auth"}).json()
    assert {item["path"] for item in files["files"]} == {"auth.py"}


def test_file_content_returns_indexed_file(client: TestClient, repo: Path) -> None:
    client.post("/ingest", json={"path": str(repo), "repo_label": "test"})
    response = client.get("/files/content", params={"path": "auth.py"})
    assert response.status_code == 200
    body = response.json()
    assert body["path"] == "auth.py"
    assert body["language"] == "python"
    assert "def create_session" in body["content"]
    assert body["total_lines"] == (repo / "auth.py").read_text(encoding="utf-8").count("\n") + 1


def test_file_content_rejects_unindexed_and_traversal(client: TestClient, repo: Path) -> None:
    client.post("/ingest", json={"path": str(repo), "repo_label": "test"})
    assert client.get("/files/content", params={"path": "nope.py"}).status_code == 404
    assert client.get("/files/content", params={"path": "../secrets.txt"}).status_code == 404


def test_chat_streams_and_cites_grounded_sources(client: TestClient, repo: Path) -> None:
    client.post("/ingest", json={"path": str(repo), "repo_label": "test"})
    response = client.post("/chat", json={"question": "how are user sessions created"})
    assert response.status_code == 200

    events = _parse_sse(response.text)
    assert any(event["type"] == "token" for event in events)
    final = next(event for event in events if event["type"] == "final")
    assert final["answer"]
    sources = final["sources"]
    assert isinstance(sources, list)
    assert sources

    # Grounding guard: every cited path exists in the index (§12).
    indexed = {item["path"] for item in client.get("/files").json()["files"]}
    for source in sources:
        assert source["path"] in indexed


def test_chat_without_index_declines_without_fabricating_sources(client: TestClient) -> None:
    response = client.post("/chat", json={"question": "where is auth handled?"})
    assert response.status_code == 200
    events = _parse_sse(response.text)
    final = next(event for event in events if event["type"] == "final")
    assert final["sources"] == []
    assert final["answer"]
