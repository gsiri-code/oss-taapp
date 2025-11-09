from __future__ import annotations

import json
import logging
from typing import Any

import pytest
from gtask_client_impl.gtask_impl import GTaskClient

import task_client_api
from tests.gtask_integration.fake_google_tasks import ExplodingService


class _ExplodingClient(GTaskClient):
    """GTaskClient wired to a service that always fails."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("tests.gtask_integration.error_paths")
        self.service: Any = ExplodingService()

    def _ensure_service_initialized(self) -> None:
        return


def _exploding_client() -> _ExplodingClient:
    return _ExplodingClient()


def test_list_tasklists_error() -> None:
    client = _exploding_client()
    result = client.list_tasklists()
    assert result == []


def test_delete_tasklist_error() -> None:
    client = _exploding_client()
    ok = client.delete_tasklist("some-id")
    assert ok is False


def test_insert_tasklist_error() -> None:
    client = _exploding_client()
    raw = json.dumps({"title": "x"})
    tl = task_client_api.tasklist.get_tasklist(raw_data=raw)
    with pytest.raises(Exception):
        client.insert_tasklist(tl)


def test_tasks_error_paths() -> None:
    client = _exploding_client()

    assert client.list_tasks("default") == []

    raw_task = json.dumps({"title": "t"})
    t = task_client_api.task.get_task(raw_data=raw_task)
    with pytest.raises(Exception):
        client.insert_task("default", t)

    assert client.delete_task("default", "task-1") is False

    with pytest.raises(ValueError):
        client.get_task("default", "task-1")
