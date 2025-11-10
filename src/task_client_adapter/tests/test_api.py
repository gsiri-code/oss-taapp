"""Tests for task_client_adapter.api helper functions."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from task_client_adapter.api import (
    delete_task_sync,
    delete_tasklist_sync,
    delete_message_sync,
    get_task_sync,
    get_message_sync,
    insert_task_sync,
    insert_tasklist_sync,
    list_messages_sync,
    list_tasklists_sync,
    list_tasks_sync,
    mark_as_read_sync,
)
from task_client_service_client import Client


def _build_client(
    *,
    status_code: int,
    payload: Any = None,
    raise_on_unexpected_status: bool = False,
) -> Client:
    """Construct a mocked Client returning a canned httpx response."""
    mock_client = Mock(spec=Client)
    mock_client.raise_on_unexpected_status = raise_on_unexpected_status

    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.json.return_value = payload
    mock_client.get_httpx_client.return_value.request.return_value = mock_response
    return mock_client


class TestListTasklistsSync:
    """Behaviour for list_tasklists_sync."""

    def test_success(self) -> None:
        client = _build_client(
            status_code=200,
            payload=[{"id": "list-1", "title": "Inbox"}],
        )

        result = list_tasklists_sync(client=client)  # type: ignore[arg-type]

        assert result == [{"id": "list-1", "title": "Inbox"}]
        client.get_httpx_client.return_value.request.assert_called_once_with(
            method="get",
            url="/tasklists",
        )

    def test_non_200_returns_none(self) -> None:
        client = _build_client(status_code=404)

        assert list_tasklists_sync(client=client) is None  # type: ignore[arg-type]

    def test_non_200_with_raise(self) -> None:
        client = _build_client(status_code=500, raise_on_unexpected_status=True)

        with pytest.raises(RuntimeError, match="Unexpected status code: 500"):
            list_tasklists_sync(client=client)  # type: ignore[arg-type]


class TestInsertTasklistSync:
    """Behaviour for insert_tasklist_sync."""

    def test_success(self) -> None:
        client = _build_client(status_code=200, payload={"id": "list-1"})

        result = insert_tasklist_sync(client=client, body={"title": "Inbox"})  # type: ignore[arg-type]

        assert result == {"id": "list-1"}
        client.get_httpx_client.return_value.request.assert_called_once_with(
            method="post",
            url="/tasklists",
            json={"title": "Inbox"},
        )

    def test_failure_returns_none(self) -> None:
        client = _build_client(status_code=400)

        assert insert_tasklist_sync(client=client, body={"title": "Inbox"}) is None  # type: ignore[arg-type]

    def test_failure_with_raise(self) -> None:
        client = _build_client(status_code=409, raise_on_unexpected_status=True)

        with pytest.raises(RuntimeError, match="Unexpected status code: 409"):
            insert_tasklist_sync(client=client, body={"title": "Inbox"})  # type: ignore[arg-type]


class TestDeleteTasklistSync:
    """Behaviour for delete_tasklist_sync."""

    def test_success(self) -> None:
        client = _build_client(status_code=200, payload={"detail": "deleted"})

        result = delete_tasklist_sync("list-1", client=client)  # type: ignore[arg-type]

        assert result == {"detail": "deleted"}
        client.get_httpx_client.return_value.request.assert_called_once_with(
            method="delete",
            url="/tasklists/list-1",
        )

    def test_failure_returns_none(self) -> None:
        client = _build_client(status_code=404)

        assert delete_tasklist_sync("list-1", client=client) is None  # type: ignore[arg-type]

    def test_failure_with_raise(self) -> None:
        client = _build_client(status_code=500, raise_on_unexpected_status=True)

        with pytest.raises(RuntimeError, match="Unexpected status code: 500"):
            delete_tasklist_sync("list-1", client=client)  # type: ignore[arg-type]


class TestListTasksSync:
    """Behaviour for list_tasks_sync."""

    def test_success(self) -> None:
        client = _build_client(
            status_code=200,
            payload=[{"id": "task-1", "title": "Call Alice"}],
        )

        result = list_tasks_sync("list-1", client=client)  # type: ignore[arg-type]

        assert result == [{"id": "task-1", "title": "Call Alice"}]
        client.get_httpx_client.return_value.request.assert_called_once_with(
            method="get",
            url="/tasks/list-1",
        )

    def test_failure_returns_none(self) -> None:
        client = _build_client(status_code=400)

        assert list_tasks_sync("list-1", client=client) is None  # type: ignore[arg-type]

    def test_failure_with_raise(self) -> None:
        client = _build_client(status_code=401, raise_on_unexpected_status=True)

        with pytest.raises(RuntimeError, match="Unexpected status code: 401"):
            list_tasks_sync("list-1", client=client)  # type: ignore[arg-type]


class TestGetTaskSync:
    """Behaviour for get_task_sync."""

    def test_success(self) -> None:
        client = _build_client(
            status_code=200,
            payload={"id": "task-1", "title": "Call Alice"},
        )

        result = get_task_sync("list-1", "task-1", client=client)  # type: ignore[arg-type]

        assert result == {"id": "task-1", "title": "Call Alice"}
        client.get_httpx_client.return_value.request.assert_called_once_with(
            method="get",
            url="/tasks/list-1/task-1",
        )

    def test_failure_returns_none(self) -> None:
        client = _build_client(status_code=404)

        assert get_task_sync("list-1", "task-1", client=client) is None  # type: ignore[arg-type]

    def test_failure_with_raise(self) -> None:
        client = _build_client(status_code=500, raise_on_unexpected_status=True)

        with pytest.raises(RuntimeError, match="Unexpected status code: 500"):
            get_task_sync("list-1", "task-1", client=client)  # type: ignore[arg-type]


class TestInsertTaskSync:
    """Behaviour for insert_task_sync."""

    def test_success(self) -> None:
        client = _build_client(
            status_code=200,
            payload={"id": "task-1", "title": "Call Alice"},
        )

        result = insert_task_sync(
            "list-1",
            client=client,  # type: ignore[arg-type]
            body={"title": "Call Alice"},
        )

        assert result == {"id": "task-1", "title": "Call Alice"}
        client.get_httpx_client.return_value.request.assert_called_once_with(
            method="post",
            url="/tasks/list-1",
            json={"title": "Call Alice"},
        )

    def test_failure_returns_none(self) -> None:
        client = _build_client(status_code=400)

        assert (
            insert_task_sync("list-1", client=client, body={"title": "Call"}) is None  # type: ignore[arg-type]
        )

    def test_failure_with_raise(self) -> None:
        client = _build_client(status_code=409, raise_on_unexpected_status=True)

        with pytest.raises(RuntimeError, match="Unexpected status code: 409"):
            insert_task_sync("list-1", client=client, body={"title": "Call"})  # type: ignore[arg-type]


class TestDeleteTaskSync:
    """Behaviour for delete_task_sync."""

    def test_success(self) -> None:
        client = _build_client(status_code=200, payload={"detail": "deleted"})

        result = delete_task_sync("list-1", "task-1", client=client)  # type: ignore[arg-type]

        assert result == {"detail": "deleted"}
        client.get_httpx_client.return_value.request.assert_called_once_with(
            method="delete",
            url="/tasks/list-1/task-1",
        )

    def test_failure_returns_none(self) -> None:
        client = _build_client(status_code=404)

        assert delete_task_sync("list-1", "task-1", client=client) is None  # type: ignore[arg-type]

    def test_failure_with_raise(self) -> None:
        client = _build_client(status_code=500, raise_on_unexpected_status=True)

        with pytest.raises(RuntimeError, match="Unexpected status code: 500"):
            delete_task_sync("list-1", "task-1", client=client)  # type: ignore[arg-type]


class TestListMessagesSync:
    """Behaviour for list_messages_sync."""

    def test_success(self) -> None:
        client = _build_client(
            status_code=200,
            payload=[{"id": "msg-1", "subject": "Hello"}],
        )

        result = list_messages_sync(client=client)  # type: ignore[arg-type]

        assert result == [{"id": "msg-1", "subject": "Hello"}]
        client.get_httpx_client.return_value.request.assert_called_once_with(
            method="get",
            url="/messages",
        )

    def test_failure_returns_none(self) -> None:
        client = _build_client(status_code=404)

        assert list_messages_sync(client=client) is None  # type: ignore[arg-type]

    def test_failure_with_raise(self) -> None:
        client = _build_client(status_code=500, raise_on_unexpected_status=True)

        with pytest.raises(RuntimeError, match="Unexpected status code: 500"):
            list_messages_sync(client=client)  # type: ignore[arg-type]


class TestGetMessageSync:
    """Behaviour for get_message_sync."""

    def test_success(self) -> None:
        client = _build_client(
            status_code=200,
            payload={"id": "msg-1", "subject": "Hello"},
        )

        result = get_message_sync("msg-1", client=client)  # type: ignore[arg-type]

        assert result == {"id": "msg-1", "subject": "Hello"}
        client.get_httpx_client.return_value.request.assert_called_once_with(
            method="get",
            url="/messages/msg-1",
        )

    def test_failure_returns_none(self) -> None:
        client = _build_client(status_code=404)

        assert get_message_sync("msg-1", client=client) is None  # type: ignore[arg-type]

    def test_failure_with_raise(self) -> None:
        client = _build_client(status_code=401, raise_on_unexpected_status=True)

        with pytest.raises(RuntimeError, match="Unexpected status code: 401"):
            get_message_sync("msg-1", client=client)  # type: ignore[arg-type]


class TestDeleteMessageSync:
    """Behaviour for delete_message_sync."""

    def test_success(self) -> None:
        client = _build_client(status_code=200, payload={"detail": "deleted"})

        result = delete_message_sync("msg-1", client=client)  # type: ignore[arg-type]

        assert result == {"detail": "deleted"}
        client.get_httpx_client.return_value.request.assert_called_once_with(
            method="delete",
            url="/messages/msg-1",
        )

    def test_failure_returns_none(self) -> None:
        client = _build_client(status_code=404)

        assert delete_message_sync("msg-1", client=client) is None  # type: ignore[arg-type]

    def test_failure_with_raise(self) -> None:
        client = _build_client(status_code=500, raise_on_unexpected_status=True)

        with pytest.raises(RuntimeError, match="Unexpected status code: 500"):
            delete_message_sync("msg-1", client=client)  # type: ignore[arg-type]


class TestMarkAsReadSync:
    """Behaviour for mark_as_read_sync."""

    def test_success(self) -> None:
        client = _build_client(status_code=200, payload={"detail": "ok"})

        result = mark_as_read_sync("msg-1", client=client)  # type: ignore[arg-type]

        assert result == {"detail": "ok"}
        client.get_httpx_client.return_value.request.assert_called_once_with(
            method="post",
            url="/messages/msg-1/mark-as-read",
        )

    def test_failure_returns_none(self) -> None:
        client = _build_client(status_code=403)

        assert mark_as_read_sync("msg-1", client=client) is None  # type: ignore[arg-type]

    def test_failure_with_raise(self) -> None:
        client = _build_client(status_code=401, raise_on_unexpected_status=True)

        with pytest.raises(RuntimeError, match="Unexpected status code: 401"):
            mark_as_read_sync("msg-1", client=client)  # type: ignore[arg-type]

