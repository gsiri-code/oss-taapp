"""Task client adapter package for wrapping auto-generated client."""

from .service_client_adapter import (
    ServiceClientAdapter,
    get_service_client_impl,
)
from .service_client_adapter import (
    register as _register_service_client,
)
from .service_task import (
    ServiceTask,
    get_service_task_impl,
)
from .service_task import (
    register as _register_service_task,
)
from .service_tasklist import (
    ServiceTaskList,
    get_service_tasklist_impl,
)
from .service_tasklist import (
    register as _register_service_tasklist,
)

__all__ = [
    "ServiceClientAdapter",
    "ServiceTask",
    "ServiceTaskList",
    "get_service_client_impl",
    "get_service_task_impl",
    "get_service_tasklist_impl",
    "register",
]


def register() -> None:
    """Register the ServiceClientAdapter, ServiceTask, and ServiceTaskList implementations."""
    _register_service_client()
    _register_service_task()
    _register_service_tasklist()


# Dependency Injection happens at import time
register()
