"""Tests for POST /tasklists."""

from __future__ import annotations

from typing import Any

import pytest

from task_client_service.dependencies import get_task_client  # type: ignore[import-untyped]
from task_client_service.routers import tasklist_router

HTTP_200_OK = 200
HTTP_409_CONFLICT = 409
HTTP_500_INTERNAL_SERVER_ERROR = 500


class _DummyTasklist:
    """Simple tasklist object returned by patched helpers."""

    def __init__(self, tasklist_id: str, title: str) -> None:
        self.id = tasklist_id
        self.title = title
        self.etag = "etag"
        self.updated = "2025-01-01T00:00:00Z"
        self.self_link = f"https://example.com/{tasklist_id}"


@pytest.mark.usefixtures("service_client")
class TestInsertTasklist:
    """Covers insert-tasklist router branches."""

    def test_insert_ok(
        self,
        service_client: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Happy path: service builds tasklist and client inserts it."""

        def fake_get_service_tasklist(_: str) -> _DummyTasklist:
            return _DummyTasklist("generated-id", "My New Task List")

        monkeypatch.setattr(tasklist_router, "get_service_tasklist", fake_get_service_tasklist)

        class FakeClient:
            def insert_tasklist(self, tl: _DummyTasklist) -> _DummyTasklist:
                return tl

        service_client.app.dependency_overrides[get_task_client] = lambda: FakeClient()

        resp = service_client.post("/tasklists", json={"title": "My New Task List"})
        assert resp.status_code == HTTP_200_OK
        data = resp.json()
        assert data["id"] == "generated-id"
        assert data["title"] == "My New Task List"

    def test_insert_conflict_409(
        self,
        service_client: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If client raises ValueError, router should return 409."""

        def fake_get_service_tasklist(_: str) -> _DummyTasklist:
            return _DummyTasklist("dup-id", "Dup Title")

        monkeypatch.setattr(tasklist_router, "get_service_tasklist", fake_get_service_tasklist)

        class FakeClient:
            def insert_tasklist(self, tl: _DummyTasklist) -> _DummyTasklist:
                msg = "already exists"
                raise ValueError(msg)

        service_client.app.dependency_overrides[get_task_client] = lambda: FakeClient()

        resp = service_client.post("/tasklists", json={"title": "Dup Title"})
        assert resp.status_code == HTTP_409_CONFLICT
        assert "already exists" in resp.json()["detail"]

    def test_insert_other_error_500(
        self,
        service_client: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If client raises non-ValueError, router should return 500."""

        def fake_get_service_tasklist(_: str) -> _DummyTasklist:
            return _DummyTasklist("some-id", "Err Title")

        monkeypatch.setattr(tasklist_router, "get_service_tasklist", fake_get_service_tasklist)

        class FakeClient:
            def insert_tasklist(self, tl: _DummyTasklist) -> _DummyTasklist:
                msg = "unexpected"
                raise RuntimeError(msg)

        service_client.app.dependency_overrides[get_task_client] = lambda: FakeClient()

        resp = service_client.post("/tasklists", json={"title": "Err Title"})
        assert resp.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert "unexpected" in resp.json()["detail"]
