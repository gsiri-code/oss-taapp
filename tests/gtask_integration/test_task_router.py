"""Tests for the task router using an in-memory client."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient
from task_client_service.fast_api_service import app

from task_client_service import dependencies

STATUS_OK = 200
STATUS_BAD_REQUEST = 400


class _MemTask:
    def __init__(self, task_id: str, title: str) -> None:
        self.id = task_id
        self.title = title
        self.notes = None
        self.status = "needsAction"
        self.due = None
        self.completed = None
        self.deleted = False
        self.hidden = False


class _InMemoryTaskClient:
    def __init__(self) -> None:
        self._tasks: dict[str, dict[str, _MemTask]] = {"default": {}}
        self._counter = 0

    def insert_task(self, tasklist_id: str, task: Any) -> _MemTask:
        self._counter += 1
        task_id = f"task-{self._counter}"
        title = getattr(task, "title", "untitled")
        obj = _MemTask(task_id, title)
        if getattr(task, "notes", None):
            obj.notes = task.notes
        if getattr(task, "status", None):
            obj.status = task.status
        if getattr(task, "due", None):
            obj.due = task.due
        self._tasks.setdefault(tasklist_id, {})
        self._tasks[tasklist_id][task_id] = obj
        return obj

    def get_task(self, tasklist_id: str, task_id: str) -> _MemTask | None:
        return self._tasks.get(tasklist_id, {}).get(task_id)

    def delete_task(self, tasklist_id: str, task_id: str) -> bool:
        tasks = self._tasks.get(tasklist_id)
        if not tasks or task_id not in tasks:
            return False
        del tasks[task_id]
        return True

    def list_tasks(self, tasklist_id: str) -> list[_MemTask]:
        return list(self._tasks.get(tasklist_id, {}).values())


_SHARED_TASK_CLIENT = _InMemoryTaskClient()


def _client() -> TestClient:
    app.dependency_overrides[dependencies.get_task_client] = (
        lambda: _SHARED_TASK_CLIENT
    )
    return TestClient(app)


def test_insert_task_ok() -> None:
    """POST /tasks/{tasklist_id} should create a task."""
    client = _client()
    body = {
        "title": "do homework",
        "notes": "math",
        "status": "needsAction",
        "due": datetime(2025, 1, 1, tzinfo=UTC).isoformat(),
    }
    resp = client.post("/tasks/default", json=body)
    assert resp.status_code == STATUS_OK
    data = resp.json()
    assert data["title"] == "do homework"
    assert "id" in data


def test_insert_task_invalid_due() -> None:
    """POST with invalid due should be rejected."""
    client = _client()
    resp = client.post("/tasks/default", json={"title": "x", "due": "bad-date"})
    assert resp.status_code == STATUS_BAD_REQUEST


def test_get_task_ok() -> None:
    """GET /tasks/{tasklist_id}/{task_id} should return the task."""
    client = _client()
    created = client.post("/tasks/default", json={"title": "t1"})
    assert created.status_code == STATUS_OK
    task_id = created.json()["id"]

    resp = client.get(f"/tasks/default/{task_id}")
    assert resp.status_code == STATUS_OK
    assert resp.json()["id"] == task_id


def test_delete_task_ok() -> None:
    """DELETE /tasks/{tasklist_id}/{task_id} should succeed for existing task."""
    client = _client()
    created = client.post("/tasks/default", json={"title": "to-delete"})
    assert created.status_code == STATUS_OK
    task_id = created.json()["id"]

    resp = client.delete(f"/tasks/default/{task_id}")
    assert resp.status_code in (200, 204)
