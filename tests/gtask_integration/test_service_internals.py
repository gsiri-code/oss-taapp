"""Tests around the FastAPI service internals (auth, deps)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi.testclient import TestClient
from task_client_service.fast_api_service import app

from task_client_service import auth_router

if TYPE_CHECKING:
    from pathlib import Path

HTTP_OK = 200
HTTP_FOUND = 302


def test_auth_login_uses_credentials(tmp_path: Path, monkeypatch: Any) -> None:
    """Login should read credentials.json and redirect."""
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text('{"installed": {"client_id": "x", "client_secret": "y"}}')
    monkeypatch.setattr(auth_router, "CREDENTIALS_PATH", str(creds_file))

    class _FakeFlow:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.redirect_uri = kwargs.get("redirect_uri")

        def authorization_url(self, *args: Any, **kwargs: Any) -> tuple[str, str]:
            return ("https://example.test/auth", "state-1")

    monkeypatch.setattr(
        auth_router,
        "Flow",
        type("F", (), {"from_client_secrets_file": lambda *_a, **_k: _FakeFlow()}),
    )

    client = TestClient(app)
    resp = client.get("/auth/login", follow_redirects=False)
    assert resp.status_code == HTTP_FOUND
