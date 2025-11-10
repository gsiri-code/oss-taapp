"""Additional unit tests for :mod:`gtask_client_impl.gtask_impl` to boost coverage."""

from __future__ import annotations

import builtins
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

import task_client_api
import gtask_client_impl.gtask_impl as gtask_impl
from gtask_client_impl.gtask_impl import GTaskClient


class FakeCredentials:
    """Lightweight stand-in for google.oauth2.credentials.Credentials."""

    def __init__(
        self,
        token: str | None = None,
        *,
        refresh_token: str | None = None,
        token_uri: str | None = None,  # noqa: ARG002 - needed for signature parity
        client_id: str | None = None,  # noqa: ARG002
        client_secret: str | None = None,  # noqa: ARG002
        scopes: list[str] | None = None,  # noqa: ARG002
    ) -> None:
        self.token = token
        self.refresh_token = refresh_token
        self.valid = token is not None
        self._refreshed = False

    def refresh(self, request: Any) -> None:  # noqa: ARG002 - signature parity
        if self.refresh_token == "bad":
            raise gtask_impl.RefreshError("bad refresh", None)
        self.valid = True
        self._refreshed = True


@pytest.fixture(autouse=True)
def clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure TASKS_* environment variables are not set between tests."""
    for var in ("TASKS_CLIENT_ID", "TASKS_CLIENT_SECRET", "TASKS_REFRESH_TOKEN", "TASKS_TOKEN_URI"):
        monkeypatch.delenv(var, raising=False)


def test_client_initializes_with_injected_service() -> None:
    """Providing a service skips authentication logic."""
    sentinel_service = object()
    client = GTaskClient(service=sentinel_service)
    assert client.service is sentinel_service


def test_client_without_credentials_sets_service_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """When no credentials are available and interactive=False, initialization succeeds with service=None."""
    monkeypatch.setattr(GTaskClient, "_get_session_credentials", lambda self: None)
    monkeypatch.setattr(GTaskClient, "_auth_from_env", lambda self: None)
    monkeypatch.setattr(GTaskClient, "_auth_from_token_file", lambda self, path: None)

    client = GTaskClient(interactive=False)
    assert client.service is None


def test_client_interactive_without_credentials_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Interactive mode should raise immediately when no credentials are present."""
    monkeypatch.setattr(GTaskClient, "_get_session_credentials", lambda self: None)
    monkeypatch.setattr(GTaskClient, "_auth_from_env", lambda self: None)
    monkeypatch.setattr(GTaskClient, "_auth_from_token_file", lambda self, path: None)

    with pytest.raises(RuntimeError):
        GTaskClient(interactive=True)


def test_get_session_credentials_from_app_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """_get_session_credentials should return credentials stored on the FastAPI app state."""
    sentinel_creds = object()

    monkeypatch.setattr(GTaskClient, "_create_credentials_from_dict", lambda self, data: sentinel_creds)

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                _current_session_creds={"token": "abc", "refresh_token": None},
            )
        ),
    )
    deps_module = __import__("task_client_service.dependencies", fromlist=["dependencies"])
    monkeypatch.setattr(deps_module, "current_request", request, raising=False)

    client = GTaskClient(service=object())
    assert client._get_session_credentials() is sentinel_creds  # noqa: SLF001 - accessing protected member for test


def test_get_session_credentials_fallback_http(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP fallback path should parse JSON credentials."""
    monkeypatch.setitem(sys.modules, "task_client_service.dependencies", SimpleNamespace(current_request=None))
    sentinel_creds = object()
    monkeypatch.setattr(GTaskClient, "_create_credentials_from_dict", lambda self, data: sentinel_creds)

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json() -> dict[str, str]:
            return {"token": "abc"}

    monkeypatch.setattr(gtask_impl.requests, "get", lambda url, timeout: FakeResponse())

    client = GTaskClient(service=object())
    assert client._get_session_credentials() is sentinel_creds  # noqa: SLF001


def test_create_credentials_from_dict_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    """The helper should refresh credentials when a refresh token is supplied."""
    monkeypatch.setattr(gtask_impl, "Credentials", FakeCredentials)
    monkeypatch.setattr(gtask_impl, "Request", lambda: None)

    client = GTaskClient(service=object())
    creds = client._create_credentials_from_dict(
        {
            "token": None,
            "refresh_token": "refresh-me",
            "client_id": "id",
            "client_secret": "secret",
        }
    )

    assert isinstance(creds, FakeCredentials)
    assert creds.valid is True
    assert creds._refreshed is True  # noqa: SLF001


def test_create_credentials_from_dict_refresh_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refresh errors should return None rather than raising."""
    monkeypatch.setattr(gtask_impl, "Credentials", FakeCredentials)
    monkeypatch.setattr(gtask_impl, "Request", lambda: None)

    client = GTaskClient(service=object())
    creds = client._create_credentials_from_dict(
        {
            "token": None,
            "refresh_token": "bad",
            "client_id": "id",
            "client_secret": "secret",
        }
    )

    assert creds is None


def test_auth_from_env_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment credentials should produce a refreshed credential object."""
    monkeypatch.setenv("TASKS_CLIENT_ID", "cid")
    monkeypatch.setenv("TASKS_CLIENT_SECRET", "secret")
    monkeypatch.setenv("TASKS_REFRESH_TOKEN", "refresh-me")
    monkeypatch.setattr(gtask_impl, "Credentials", FakeCredentials)
    monkeypatch.setattr(gtask_impl, "Request", lambda: None)

    client = GTaskClient(service=object())
    creds = client._auth_from_env()

    assert isinstance(creds, FakeCredentials)
    assert creds.valid is True


def test_auth_from_token_file_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Token files should be loaded and, if necessary, refreshed."""
    token_file = tmp_path / "token.json"
    token_file.write_text(json.dumps({"token": "abc"}))

    fake_creds = FakeCredentials(token="abc")
    monkeypatch.setattr(
        gtask_impl.Credentials,
        "from_authorized_user_file",
        lambda path, scopes: fake_creds,
    )
    monkeypatch.setattr(gtask_impl, "Request", lambda: None)

    client = GTaskClient(service=object())
    creds = client._auth_from_token_file(str(token_file))

    assert creds is fake_creds


def test_auth_from_env_refresh_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refresh failures in env authentication should return None."""
    monkeypatch.setenv("TASKS_CLIENT_ID", "cid")
    monkeypatch.setenv("TASKS_CLIENT_SECRET", "secret")
    monkeypatch.setenv("TASKS_REFRESH_TOKEN", "bad")
    monkeypatch.setattr(gtask_impl, "Credentials", FakeCredentials)
    monkeypatch.setattr(gtask_impl, "Request", lambda: None)

    client = GTaskClient(service=object())
    assert client._auth_from_env() is None


def test_auth_from_token_file_handles_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Token loading errors should return None."""
    token_file = tmp_path / "token.json"
    token_file.write_text("{}")

    def raise_error(path: str, scopes: list[str]) -> None:  # noqa: ARG001
        raise ValueError("bad token")

    monkeypatch.setattr(gtask_impl.Credentials, "from_authorized_user_file", raise_error)

    client = GTaskClient(service=object())
    assert client._auth_from_token_file(str(token_file)) is None


def test_save_token_writes_file(tmp_path: Path) -> None:
    """_save_token should persist the credential JSON."""
    token_file = tmp_path / "out.json"
    client = GTaskClient(service=object())

    class SerializeCreds:
        def to_json(self) -> str:
            return '{"token": "xyz"}'

    client._save_token(SerializeCreds(), str(token_file))  # noqa: SLF001
    assert token_file.read_text() == '{"token": "xyz"}'

def test_get_client_impl_and_register(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_client_impl and register should wire up the task_client_api factory."""
    fake_client = MagicMock()
    monkeypatch.setattr(gtask_impl, "GTaskClient", MagicMock(return_value=fake_client))

    result = gtask_impl.get_client_impl(interactive=True)
    gtask_impl.GTaskClient.assert_called_once_with(interactive=True)
    assert result is fake_client

    gtask_impl.register()
    assert task_client_api.get_client(interactive=False) is fake_client


def test_ensure_service_initialized_builds_service(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the client has no service, _ensure_service_initialized should construct one."""
    stub_creds = SimpleNamespace(valid=True, refresh_token=None)

    monkeypatch.setattr(GTaskClient, "_get_session_credentials", lambda self: None)
    monkeypatch.setattr(GTaskClient, "_auth_from_env", lambda self: stub_creds)
    monkeypatch.setattr(GTaskClient, "_auth_from_token_file", lambda self, path: None)
    monkeypatch.setattr(gtask_impl, "build", lambda api, version, credentials: "SERVICE")

    client = GTaskClient(service=object())
    client.service = None

    client._ensure_service_initialized()  # noqa: SLF001
    assert client.service == "SERVICE"


def test_ensure_service_initialized_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """If no credential source succeeds, a RuntimeError should be raised."""
    monkeypatch.setattr(GTaskClient, "_get_session_credentials", lambda self: None)
    monkeypatch.setattr(GTaskClient, "_auth_from_env", lambda self: None)
    monkeypatch.setattr(GTaskClient, "_auth_from_token_file", lambda self, path: None)

    client = GTaskClient(service=object())
    client.service = None

    with pytest.raises(RuntimeError):
        client._ensure_service_initialized()  # noqa: SLF001


def test_client_init_refresh_failure_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refresh errors during initialization should surface as RuntimeError."""
    bad_creds = FakeCredentials(token=None, refresh_token="bad")
    bad_creds.valid = False
    monkeypatch.setattr(GTaskClient, "_get_session_credentials", lambda self: bad_creds)
    monkeypatch.setattr(GTaskClient, "_auth_from_env", lambda self: None)
    monkeypatch.setattr(GTaskClient, "_auth_from_token_file", lambda self, path: None)
    monkeypatch.setattr(gtask_impl, "Request", lambda: None)

    with pytest.raises(RuntimeError):
        GTaskClient()


def test_ensure_service_initialized_refresh_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """_ensure_service_initialized should raise when refresh fails."""
    bad_creds = FakeCredentials(token=None, refresh_token="bad")
    bad_creds.valid = False
    monkeypatch.setattr(GTaskClient, "_get_session_credentials", lambda self: None)
    monkeypatch.setattr(GTaskClient, "_auth_from_env", lambda self: bad_creds)
    monkeypatch.setattr(GTaskClient, "_auth_from_token_file", lambda self, path: None)
    monkeypatch.setattr(gtask_impl, "Request", lambda: None)

    client = GTaskClient(service=object())
    client.service = None

    with pytest.raises(RuntimeError):
        client._ensure_service_initialized()  # noqa: SLF001


def test_client_initializes_using_session_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid session credentials should be refreshed and used to build the service."""
    fake_creds = FakeCredentials(token=None, refresh_token="refresh-me")
    fake_creds.valid = False
    monkeypatch.setattr(GTaskClient, "_get_session_credentials", lambda self: fake_creds)
    monkeypatch.setattr(GTaskClient, "_auth_from_env", lambda self: None)
    monkeypatch.setattr(GTaskClient, "_auth_from_token_file", lambda self, path: None)
    monkeypatch.setattr(gtask_impl, "Request", lambda: None)
    monkeypatch.setattr(gtask_impl, "build", lambda api, version, credentials: "SERVICE")

    client = GTaskClient()

    assert client.service == "SERVICE"
    assert fake_creds.valid is True
    assert fake_creds._refreshed is True  # noqa: SLF001


def test_delete_tasklist_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """delete_tasklist should return True when the underlying API succeeds."""
    client = GTaskClient(service=object())
    service = MagicMock()
    delete_mock = MagicMock()
    delete_mock.execute.return_value = None
    service.tasklists.return_value.delete.return_value = delete_mock

    client.service = service
    monkeypatch.setattr(GTaskClient, "_ensure_service_initialized", lambda self: None)

    assert client.delete_tasklist("abc")
    service.tasklists.assert_called_once()
    delete_mock.execute.assert_called_once()


def test_delete_tasklist_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """delete_tasklist should swallow API errors and return False."""
    client = GTaskClient(service=object())
    service = MagicMock()
    delete_mock = MagicMock()
    delete_mock.execute.side_effect = ValueError("boom")
    service.tasklists.return_value.delete.return_value = delete_mock

    client.service = service
    monkeypatch.setattr(GTaskClient, "_ensure_service_initialized", lambda self: None)

    assert client.delete_tasklist("abc") is False


def test_insert_tasklist_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """insert_tasklist should convert the API payload via task_client_api."""
    client = GTaskClient(service=object())
    service = MagicMock()
    insert_mock = MagicMock()
    insert_mock.execute.return_value = {"id": "1", "title": "Hello"}
    service.tasklists.return_value.insert.return_value = insert_mock
    client.service = service
    monkeypatch.setattr(GTaskClient, "_ensure_service_initialized", lambda self: None)
    monkeypatch.setattr(
        gtask_impl.task_client_api.tasklist,
        "get_tasklist",
        lambda raw_data: f"converted:{raw_data}",
    )

    result = client.insert_tasklist(SimpleNamespace(title="Hello"))
    assert result.startswith("converted:")


def test_insert_tasklist_raises_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """insert_tasklist should propagate API exceptions."""
    client = GTaskClient(service=object())
    service = MagicMock()
    insert_mock = MagicMock()
    insert_mock.execute.side_effect = ValueError("boom")
    service.tasklists.return_value.insert.return_value = insert_mock
    client.service = service
    monkeypatch.setattr(GTaskClient, "_ensure_service_initialized", lambda self: None)

    with pytest.raises(ValueError):
        client.insert_tasklist(SimpleNamespace(title="Hello"))


def test_list_tasklists_handles_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_tasklists should return an empty list when the API raises."""
    client = GTaskClient(service=object())
    service = MagicMock()
    service.tasklists.return_value.list.return_value.execute.side_effect = ValueError("boom")
    client.service = service
    monkeypatch.setattr(GTaskClient, "_ensure_service_initialized", lambda self: None)

    assert client.list_tasklists() == []


def test_list_tasklists_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_tasklists should convert each item via tasklist.get_tasklist."""
    client = GTaskClient(service=object())
    service = MagicMock()
    service.tasklists.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "1", "title": "First"}],
    }
    client.service = service
    monkeypatch.setattr(GTaskClient, "_ensure_service_initialized", lambda self: None)
    monkeypatch.setattr(gtask_impl.tasklist, "get_tasklist", lambda raw_data: raw_data)

    result = client.list_tasklists()
    assert result == [json.dumps({"id": "1", "title": "First"})]


def test_list_tasks_handles_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_tasks should return an empty list on exceptions."""
    client = GTaskClient(service=object())
    service = MagicMock()
    service.tasks.return_value.list.return_value.execute.side_effect = ValueError("boom")
    client.service = service
    monkeypatch.setattr(GTaskClient, "_ensure_service_initialized", lambda self: None)

    assert client.list_tasks("abc") == []


def test_list_tasks_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_tasks should convert each item via task.get_task."""
    client = GTaskClient(service=object())
    service = MagicMock()
    service.tasks.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "1", "title": "Task"}],
    }
    client.service = service
    monkeypatch.setattr(GTaskClient, "_ensure_service_initialized", lambda self: None)
    monkeypatch.setattr(gtask_impl.task, "get_task", lambda raw_data: raw_data)

    result = client.list_tasks("list-id")
    assert result == [json.dumps({"id": "1", "title": "Task"})]


def test_insert_task_includes_optional_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """insert_task should forward optional fields to the API."""
    client = GTaskClient(service=object())
    service = MagicMock()
    insert_mock = MagicMock()
    insert_mock.execute.return_value = {"id": "t1", "title": "Task"}
    tasks_api = service.tasks.return_value
    tasks_api.insert.return_value = insert_mock
    client.service = service
    monkeypatch.setattr(GTaskClient, "_ensure_service_initialized", lambda self: None)
    monkeypatch.setattr(gtask_impl.task_client_api.task, "get_task", lambda raw_data: raw_data)

    task_obj = SimpleNamespace(
        title="Task",
        notes="Notes",
        status="completed",
        due="2025-01-01T00:00:00Z",
    )

    client.insert_task("list-id", task_obj)

    tasks_api.insert.assert_called_once_with(
        tasklist="list-id",
        body={
            "title": "Task",
            "notes": "Notes",
            "status": "completed",
            "due": "2025-01-01T00:00:00Z",
        },
    )


def test_insert_task_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """insert_task should build the request body and return the converted task."""
    client = GTaskClient(service=object())
    service = MagicMock()
    service.tasks.return_value.insert.return_value.execute.return_value = {
        "id": "t1",
        "title": "Task",
    }
    client.service = service
    monkeypatch.setattr(GTaskClient, "_ensure_service_initialized", lambda self: None)
    monkeypatch.setattr(gtask_impl.task_client_api.task, "get_task", lambda raw_data: f"task:{raw_data}")

    result = client.insert_task("list-id", SimpleNamespace(title="Task", notes=None, status=None, due=None))
    assert result.startswith("task:")


def test_insert_task_raises_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """insert_task should re-raise exceptions from the API."""
    client = GTaskClient(service=object())
    service = MagicMock()
    insert_mock = MagicMock()
    insert_mock.execute.side_effect = ValueError("boom")
    service.tasks.return_value.insert.return_value = insert_mock
    client.service = service
    monkeypatch.setattr(GTaskClient, "_ensure_service_initialized", lambda self: None)

    with pytest.raises(ValueError):
        client.insert_task(
            "list-id",
            SimpleNamespace(title="Task", notes=None, status=None, due=None),
        )


def test_delete_task_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """delete_task should return True when no exception is raised."""
    client = GTaskClient(service=object())
    service = MagicMock()
    service.tasks.return_value.delete.return_value.execute.return_value = None
    client.service = service
    monkeypatch.setattr(GTaskClient, "_ensure_service_initialized", lambda self: None)

    assert client.delete_task("list-id", "task-id") is True


def test_delete_task_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """delete_task should return False when the API raises."""
    client = GTaskClient(service=object())
    service = MagicMock()
    service.tasks.return_value.delete.return_value.execute.side_effect = ValueError("boom")
    client.service = service
    monkeypatch.setattr(GTaskClient, "_ensure_service_initialized", lambda self: None)

    assert client.delete_task("list-id", "task-id") is False


def test_get_task_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_task should return the converted task payload."""
    client = GTaskClient(service=object())
    service = MagicMock()
    service.tasks.return_value.get.return_value.execute.return_value = {
        "id": "task-id",
        "title": "Task",
    }
    client.service = service
    monkeypatch.setattr(GTaskClient, "_ensure_service_initialized", lambda self: None)
    monkeypatch.setattr(gtask_impl.task, "get_task", lambda raw_data: raw_data)

    assert client.get_task("list-id", "task-id") == json.dumps({"id": "task-id", "title": "Task"})


def test_get_task_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_task should raise ValueError when the API call fails."""
    client = GTaskClient(service=object())
    service = MagicMock()
    service.tasks.return_value.get.return_value.execute.side_effect = ValueError("boom")
    client.service = service
    monkeypatch.setattr(GTaskClient, "_ensure_service_initialized", lambda self: None)

    with pytest.raises(ValueError):
        client.get_task("list-id", "task-id")


def test_get_session_credentials_http_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unauthorized HTTP responses should yield None."""
    deps_module = __import__("task_client_service.dependencies", fromlist=["dependencies"])
    monkeypatch.setattr(deps_module, "current_request", None, raising=False)

    class FakeResponse:
        status_code = 401

    monkeypatch.setattr(gtask_impl.requests, "get", lambda url, timeout: FakeResponse())

    client = GTaskClient(service=object())
    assert client._get_session_credentials() is None  # noqa: SLF001


def test_get_session_credentials_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-success HTTP responses should also return None."""
    deps_module = __import__("task_client_service.dependencies", fromlist=["dependencies"])
    monkeypatch.setattr(deps_module, "current_request", None, raising=False)

    class FakeResponse:
        status_code = 500

    monkeypatch.setattr(gtask_impl.requests, "get", lambda url, timeout: FakeResponse())

    client = GTaskClient(service=object())
    assert client._get_session_credentials() is None  # noqa: SLF001


def test_get_session_credentials_json_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """JSON parsing errors should be caught."""
    deps_module = __import__("task_client_service.dependencies", fromlist=["dependencies"])
    monkeypatch.setattr(deps_module, "current_request", None, raising=False)

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json() -> Any:
            raise ValueError("bad json")

    monkeypatch.setattr(gtask_impl.requests, "get", lambda url, timeout: FakeResponse())

    client = GTaskClient(service=object())
    assert client._get_session_credentials() is None  # noqa: SLF001


def test_get_session_credentials_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Import errors for the dependencies module should be handled gracefully."""
    original_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "task_client_service.dependencies":
            raise ImportError("not available")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(gtask_impl.requests, "get", lambda url, timeout: type("Resp", (), {"status_code": 401})())  # noqa: ANN401

    client = GTaskClient(service=object())
    assert client._get_session_credentials() is None  # noqa: SLF001

