"""Public export surface for ``mail_client_api``."""

from task_client_api.client import Client, get_client
from task_client_api.task import Task
from task_client_api.tasklist import TaskList

__all__ = [
    "Client",
    "Task",
    "TaskList",
    "get_client",
    "get_task",
    "get_tasklist",
    "task",
    "tasklist",
]
