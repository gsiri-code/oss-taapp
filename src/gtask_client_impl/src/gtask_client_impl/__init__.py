"""Public exports for the Google Tasks client implementation package."""

from gtask_client_impl.gtask_impl import (
    GTaskClient,
    get_client_impl,
)
from gtask_client_impl.gtask_impl import (
    register as _register_client,
)
from gtask_client_impl.task_impl import (
    GTask,
    get_task_impl,
)
from gtask_client_impl.task_impl import (
    register as _register_task,
)
from gtask_client_impl.tasklist_impl import (
    GTaskList,
    get_tasklist_impl,
)
from gtask_client_impl.tasklist_impl import (
    register as _register_tasklist,
)

__all__ = [
    "GTask",
    "GTaskClient",
    "GTaskList",
    "get_client_impl",
    "get_task_impl",
    "get_tasklist_impl",
    "register",
]


def register() -> None:
    """Register the Google Tasks client, task, and tasklist implementations."""
    _register_client()
    _register_task()
    _register_tasklist()


# Dependency Injection happens at import time
register()
