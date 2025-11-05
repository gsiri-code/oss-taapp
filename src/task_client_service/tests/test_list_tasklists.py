"""Tests for GET /tasklists."""

from __future__ import annotations

from typing import Any

import pytest

from task_client_service import fast_api_service
from task_client_service.dependencies import get_task_client  # type: ignore[import-untyped]

HTTP_200_OK = 200
HTTP_500_INTERNAL_SERVER_ERROR = 500


class _TL:
    """Stub tasklist used to emulate backend list responses."""

    def __init__(self, tasklist_id: str) -> None:
        self.id = tasklist_id
        self.title = f"title-{tasklist_id}"
        self.etag = "etag"
        self.updated = "2025-01-01T00:00:00Z"
        self.self_link = f"https://example.com/{tasklist_id}"


@pytest.mark.usefixtures("service_client")
class TestListTasklists:
    """Covers list-tasklists router branches."""

    def test_list_tasklists_ok(self, service_client: Any) -> None:
        """Client returns 2 tasklists -> 200 and list."""

        class FakeClient:
            def list_tasklists(self) -> list[_TL]:
                return [_TL("tl1"), _TL("tl2")]

        service_client.app.dependency_overrides[get_task_client] = lambda: FakeClient()

        resp = service_client.get("/tasklists")
        assert resp.status_code == HTTP_200_OK
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["id"] == "tl1"
        assert data[1]["id"] == "tl2"

    def test_list_tasklists_server_error(self, service_client: Any) -> None:
        """Client raises -> router returns 500."""

        class BoomClient:
            def list_tasklists(self) -> list[Any]:
                msg = "backend died"
                raise RuntimeError(msg)

        service_client.app.dependency_overrides[get_task_client] = lambda: BoomClient()

        resp = service_client.get("/tasklists")
        assert resp.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert "backend died" in resp.json()["detail"]


def test_lifespan_starts_successfully(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lifespan should init client and shut down cleanly."""

    class DummyClient:
        """Fake task client."""

    def fake_get_client(*, interactive: bool = False) -> DummyClient:
        return DummyClient()

    monkeypatch.setattr(fast_api_service, "get_client", fake_get_client)

    from fastapi.testclient import TestClient

    with TestClient(fast_api_service.app):
        pass


def test_lifespan_init_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lifespan should propagate errors from get_client."""
    err_msg = "boom from get_client"

    def fake_get_client(*, interactive: bool = False) -> None:
        raise RuntimeError(err_msg)

    monkeypatch.setattr(fast_api_service, "get_client", fake_get_client)

    from fastapi.testclient import TestClient

    with pytest.raises(RuntimeError, match=err_msg), TestClient(fast_api_service.app):
        pass
