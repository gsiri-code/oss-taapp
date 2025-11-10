"""Tests for task_client_service.dependencies.get_task_client."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from task_client_service import dependencies


def _build_request_with_session(session_data: dict[str, Any]) -> Request:
    """Create a Request with pre-populated session/app state."""
    app = FastAPI()
    app.state._current_session_creds = None  # type: ignore[attr-defined]
    client = TestClient(app)
    request = client.build_request("GET", "/")
    request.session.update(session_data)  # type: ignore[attr-defined]
    request._app = app  # type: ignore[attr-defined]
    return request


def test_get_task_client_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Session credentials should be stored on app state and client returned."""
    fake_client = MagicMock()
    monkeypatch.setattr(dependencies, "get_client", MagicMock(return_value=fake_client))

    session_payload = {"credentials": json.dumps({"token": "abc"})}
    request = _build_request_with_session(session_payload)

    result = dependencies.get_task_client(request)

    assert result is fake_client
    assert request.app.state._current_session_creds == {"token": "abc"}  # type: ignore[attr-defined]


def test_get_task_client_handles_unparsable_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid JSON should be logged but not crash the dependency."""
    fake_client = MagicMock()
    monkeypatch.setattr(dependencies, "get_client", MagicMock(return_value=fake_client))

    request = _build_request_with_session({"credentials": "not-json"})

    result = dependencies.get_task_client(request)

    assert result is fake_client
    assert request.app.state._current_session_creds is None  # type: ignore[attr-defined]


def test_get_task_client_runtime_error_raises_http_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """RuntimeError from get_client should map to HTTP 401."""
    monkeypatch.setattr(
        dependencies,
        "get_client",
        MagicMock(side_effect=RuntimeError("no creds")),
    )

    request = _build_request_with_session({})

    with pytest.raises(dependencies.HTTPException) as exc:
        dependencies.get_task_client(request)

    assert exc.value.status_code == 401


def test_get_task_client_generic_error_raises_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unexpected exceptions should map to HTTP 503."""
    monkeypatch.setattr(
        dependencies,
        "get_client",
        MagicMock(side_effect=ValueError("boom")),
    )

    request = _build_request_with_session({})

    with pytest.raises(dependencies.HTTPException) as exc:
        dependencies.get_task_client(request)

    assert exc.value.status_code == 503

