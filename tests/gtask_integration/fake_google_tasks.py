"""Small fakes for Google Tasks used by integration tests."""

from __future__ import annotations


class _Operation:
    """Tiny object that mimics googleapiclient's .execute()."""

    def __init__(self, payload: object) -> None:
        """Store the payload to be returned on execute()."""
        self._payload = payload

    def execute(self) -> object:
        """Return the stored payload."""
        return self._payload


class FakeTasks:
    """Fake tasks collection."""

    def __init__(self) -> None:
        """Initialize an in-memory tasks dict."""
        self._tasks: dict[str, dict[str, dict[str, object]]] = {"default": {}}
        self._counter = 0

    def list(self, *, tasklist: str) -> _Operation:
        """List tasks under a tasklist."""
        items = list(self._tasks.get(tasklist, {}).values())
        return _Operation({"items": items})

    def insert(self, *, tasklist: str, body: dict[str, object]) -> _Operation:
        """Insert a task."""
        self._counter += 1
        task_id = f"task-{self._counter}"
        stored = {"id": task_id, **body}
        self._tasks.setdefault(tasklist, {})[task_id] = stored
        return _Operation(stored)

    def get(self, *, tasklist: str, task: str) -> _Operation:
        """Get a task."""
        item = self._tasks.get(tasklist, {}).get(task)
        return _Operation(item)

    def delete(self, *, tasklist: str, task: str) -> _Operation:
        """Delete a task (no error if missing)."""
        tasks = self._tasks.get(tasklist)
        if tasks and task in tasks:
            del tasks[task]
        return _Operation({})


class FakeTasklists:
    """Fake tasklists collection."""

    def __init__(self) -> None:
        """Start with a single default list."""
        self._lists: list[dict[str, object]] = [
            {"id": "default", "title": "Default List"},
        ]
        self._counter = 1

    def list(self) -> _Operation:
        """List tasklists."""
        return _Operation({"items": self._lists})

    def insert(self, *, body: dict[str, object]) -> _Operation:
        """Insert a tasklist."""
        self._counter += 1
        list_id = f"list-{self._counter}"
        stored = {"id": list_id, **body}
        self._lists.append(stored)
        return _Operation(stored)

    def delete(self, *, tasklist: str) -> _Operation:
        """Delete a tasklist except the default one."""
        self._lists = [
            item
            for item in self._lists
            if not (item["id"] == tasklist and item["id"] != "default")
        ]
        return _Operation({})


class FakeTasksService:
    """Top-level fake service object."""

    def __init__(self) -> None:
        """Create fake tasks and tasklists."""
        self._tasks = FakeTasks()
        self._tasklists = FakeTasklists()

    def tasks(self) -> FakeTasks:
        """Return tasks collection."""
        return self._tasks

    def tasklists(self) -> FakeTasklists:
        """Return tasklists collection."""
        return self._tasklists


# exploding fakes ↓


class ExplodingTasks:
    """Tasks collection that raises on every call."""

    def list(self, *, tasklist: str) -> _Operation:  # noqa: ARG002
        """Raise on list."""
        msg = "boom tasks list"
        raise ValueError(msg)

    def insert(self, *, tasklist: str, body: dict[str, object]) -> _Operation:  # noqa: ARG002
        """Raise on insert."""
        msg = "boom task insert"
        raise ValueError(msg)

    def get(self, *, tasklist: str, task: str) -> _Operation:  # noqa: ARG002
        """Raise on get."""
        msg = "boom task get"
        raise ValueError(msg)

    def delete(self, *, tasklist: str, task: str) -> _Operation:  # noqa: ARG002
        """Raise on delete."""
        msg = "boom task delete"
        raise ValueError(msg)


class ExplodingService:
    """Service that always raises."""

    def tasks(self) -> ExplodingTasks:
        """Return the exploding tasks collection."""
        return ExplodingTasks()

    def tasklists(self) -> None:
        """Raise on tasklists access."""
        msg = "boom tasklists"
        raise ValueError(msg)
