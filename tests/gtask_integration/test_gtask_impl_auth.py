"""Tests for auth endpoints exposed by the service."""

from fastapi.testclient import TestClient
from task_client_service.fast_api_service import app

HTTP_UNAUTHORIZED = 401


def test_get_session_creds_without_auth() -> None:
    """Should return 401 if session has no credentials."""
    client = TestClient(app)
    resp = client.get("/auth/_give_session_creds")
    assert resp.status_code == HTTP_UNAUTHORIZED
