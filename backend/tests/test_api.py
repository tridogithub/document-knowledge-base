import io

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def project_id(client):
    r = client.post("/api/projects", json={"name": "apitest"})
    if r.status_code == 409:
        pid = next(p["id"] for p in client.get("/api/projects").json() if p["name"] == "apitest")
    else:
        pid = r.json()["id"]
    yield pid
    client.delete(f"/api/projects/{pid}")


def test_create_duplicate_project(client, project_id):
    assert client.post("/api/projects", json={"name": "apitest"}).status_code == 409


def test_invalid_project_name(client):
    assert client.post("/api/projects", json={"name": "  "}).status_code == 422


def test_upload_unsupported_extension(client, project_id):
    r = client.post(
        f"/api/projects/{project_id}/files",
        files=[("files", ("evil.exe", io.BytesIO(b"x"), "application/octet-stream"))],
    )
    assert r.status_code == 400
    assert "Unsupported" in r.json()["detail"]


def test_search_query_too_long(client, project_id):
    r = client.get(f"/api/projects/{project_id}/search", params={"q": "x" * 600})
    assert r.status_code == 422


def test_search_empty_query(client, project_id):
    r = client.get(f"/api/projects/{project_id}/search", params={"q": "  "})
    assert r.status_code == 422


def test_search_empty_project(client, project_id):
    r = client.get(f"/api/projects/{project_id}/search", params={"q": "anything"})
    assert r.status_code == 200
    assert r.json()["results"] == []


def test_mcp_info(client):
    body = client.get("/api/mcp-info").json()
    assert body["url"].endswith("/mcp")
    assert "mcpServers" in body["config_json"]
