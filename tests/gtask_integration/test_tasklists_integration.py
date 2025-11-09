"""End-to-end checks for tasklists endpoints."""

from fastapi.testclient import TestClient
from task_client_service.fast_api_service import app

HTTP_OK = 200


def test_list_tasklists_roundtrip() -> None:
    """List should return at least the default list."""
    client = TestClient(app)
    resp = client.get("/tasklists")
    assert resp.status_code == HTTP_OK
    data = resp.json()
    assert data
