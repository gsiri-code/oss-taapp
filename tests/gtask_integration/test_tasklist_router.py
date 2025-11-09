"""Tests for the tasklist router using an in-memory client."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from task_client_service.fast_api_service import app

from task_client_service import dependencies

STATUS_OK = 200


class _MemTaskList:
    def __init__(self, list_id: str, title: str) -> None:
        self.id = list_id
        self.title = title
        self.etag = f"etag-{list_id}"
        self.updated = "2025-01-01T00:00:00Z"
        self.self_link = f"https://example.test/tasklists/{list_id}"


class _InMemoryTaskListClient:
    def __init__(self) -> None:
        self._lists: list[_MemTaskList] = [_MemTaskList("default", "Default List")]
        self._counter = 1

    def list_tasklists(self) -> list[_MemTaskList]:
        return self._lists

    def insert_tasklist(self, tl: Any) -> _MemTaskList:
        self._counter += 1
        list_id = f"list-{self._counter}"
        title = getattr(tl, "title", "Untitled")
        obj = _MemTaskList(list_id, title)
        self._lists.append(obj)
        return obj

    def delete_tasklist(self, tasklist_id: str) -> bool:
        for idx, tl in enumerate(self._lists):
            if tl.id == tasklist_id:
                if idx == 0:
                    return False
                del self._lists[idx]
                return True
        return False


_SHARED_TL_CLIENT = _InMemoryTaskListClient()


def _client() -> TestClient:
    app.dependency_overrides[dependencies.get_task_client] = (
        lambda: _SHARED_TL_CLIENT
    )
    return TestClient(app)


def test_list_tasklists_ok() -> None:
    """GET /tasklists should return at least the default list."""
    client = _client()
    resp = client.get("/tasklists")
    assert resp.status_code == STATUS_OK
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["id"] == "default"
    assert "self_link" in data[0]


def test_insert_tasklist_ok() -> None:
    """POST /tasklists should create a new list."""
    client = _client()
    resp = client.post("/tasklists", json={"title": "Extra"})
    assert resp.status_code == STATUS_OK
    data = resp.json()
    assert data["title"] == "Extra"
    assert data["id"].startswith("list-")
    assert "self_link" in data


def test_delete_tasklist_success() -> None:
    """DELETE /tasklists/{tasklist_id} should succeed for non-default list."""
    client = _client()
    created = client.post("/tasklists", json={"title": "Extra"})
    assert created.status_code == STATUS_OK
    list_id = created.json()["id"]

    resp = client.delete(f"/tasklists/{list_id}")
    assert resp.status_code in (200, 204)
