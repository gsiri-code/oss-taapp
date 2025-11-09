from __future__ import annotations

import importlib
import json
import logging
import os
import sys
import types
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from gtask_client_impl.gtask_impl import GTaskClient

import task_client_api
from tests.gtask_integration.fake_google_tasks import FakeTasksService

MODULE_PATH = "gtask_client_impl.gtask_impl"


class _FakeServiceClient(GTaskClient):
    """GTaskClient variant that uses the in-memory fake service."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("tests.gtask_integration.gtask_impl")
        self.service: Any = FakeTasksService()

    def _ensure_service_initialized(self) -> None:
        return


def _make_client_with_fake_service() -> GTaskClient:
    return _FakeServiceClient()


def test_list_tasklists_direct() -> None:
    client = _make_client_with_fake_service()
    lists_ = client.list_tasklists()
    assert len(lists_) == 1
    # the fake service in tests.gtask_integration.fake_google_tasks returns this title
    assert lists_[0].title == "Default List"


def test_insert_tasklist_direct() -> None:
    client = _make_client_with_fake_service()
    raw = json.dumps({"title": "New List"})
    tl = task_client_api.tasklist.get_tasklist(raw_data=raw)
    created = client.insert_tasklist(tl)
    assert created.title == "New List"

    lists_ = client.list_tasklists()
    assert any(item.title == "New List" for item in lists_)


def test_delete_tasklist_direct() -> None:
    client = _make_client_with_fake_service()
    raw = json.dumps({"title": "To Delete"})
    tl = task_client_api.tasklist.get_tasklist(raw_data=raw)
    created = client.insert_tasklist(tl)

    ok = client.delete_tasklist(created.id)
    assert ok

    lists_ = client.list_tasklists()
    assert not any(item.id == created.id for item in lists_)


def test_task_crud_direct() -> None:
    client = _make_client_with_fake_service()

    raw_task = json.dumps(
        {
            "title": "do hw",
            "notes": "integration",
            "status": "needsAction",
        }
    )
    t = task_client_api.task.get_task(raw_data=raw_task)
    created = client.insert_task("default", t)
    assert created.title == "do hw"

    tasks = client.list_tasks("default")
    assert any(task.title == "do hw" for task in tasks)

    fetched = client.get_task("default", created.id)
    assert fetched.id == created.id

    ok = client.delete_task("default", created.id)
    assert ok
    tasks_after = client.list_tasks("default")
    assert not any(task.id == created.id for task in tasks_after)


def _reload_without_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> ModuleType:
    """Re-import gtask_impl while pretending python-dotenv is missing."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("FROM_ENV=YES\n", encoding="utf-8")

    if MODULE_PATH in sys.modules:
        del sys.modules[MODULE_PATH]

    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        if name == "dotenv":
            raise ImportError("no python-dotenv here")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    mod = importlib.import_module(MODULE_PATH)
    return mod


def test_module_fallback_env_loader(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    mod = _reload_without_dotenv(tmp_path, monkeypatch)
    assert os.environ.get("FROM_ENV") == "YES"
    importlib.reload(mod)


def test_init_uses_session_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise __init__ branch where session creds exist."""
    import gtask_client_impl.gtask_impl as gi

    class FakeCreds:
        def __init__(self) -> None:
            self.valid = True
            self.refresh_token = None

    monkeypatch.setattr(
        gi.GTaskClient,
        "_get_session_credentials",
        lambda self: FakeCreds(),
    )

    def fake_build(*_args: Any, **_kwargs: Any) -> Any:
        return types.SimpleNamespace(
            tasklists=lambda: None,
            tasks=lambda: None,
        )

    monkeypatch.setattr(gi, "build", fake_build)

    client = gi.GTaskClient()
    assert client.service is not None


def test_init_interactive_no_creds_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise interactive=True path that raises RuntimeError when no creds exist."""
    import gtask_client_impl.gtask_impl as gi

    monkeypatch.setattr(gi.GTaskClient, "_get_session_credentials", lambda self: None)
    monkeypatch.setattr(gi.GTaskClient, "_auth_from_env", lambda self: None)
    monkeypatch.setattr(gi.GTaskClient, "_auth_from_token_file", lambda self, p: None)

    with pytest.raises(RuntimeError):
        gi.GTaskClient(interactive=True)


def test_auth_from_env_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise _auth_from_env success branch."""
    import gtask_client_impl.gtask_impl as gi

    monkeypatch.setenv("TASKS_CLIENT_ID", "cid")
    monkeypatch.setenv("TASKS_CLIENT_SECRET", "sec")
    monkeypatch.setenv("TASKS_REFRESH_TOKEN", "rtok")

    class FakeCreds:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.valid = True

        def refresh(self, _req: Any) -> None:
            return None

    monkeypatch.setattr(gi, "Credentials", FakeCreds)

    c = gi.GTaskClient.__new__(gi.GTaskClient)
    res = c._auth_from_env()
    assert res is not None
    assert res.valid is True


def test_auth_from_env_refresh_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise _auth_from_env branch where refresh fails."""
    import gtask_client_impl.gtask_impl as gi

    monkeypatch.setenv("TASKS_CLIENT_ID", "cid")
    monkeypatch.setenv("TASKS_CLIENT_SECRET", "sec")
    monkeypatch.setenv("TASKS_REFRESH_TOKEN", "rtok")

    class BadCreds:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.valid = False

        def refresh(self, _req: Any) -> None:
            raise ValueError("refresh failed")

    monkeypatch.setattr(gi, "Credentials", BadCreds)

    c = gi.GTaskClient.__new__(gi.GTaskClient)
    res = c._auth_from_env()
    assert res is None
