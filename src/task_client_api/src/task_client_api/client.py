"""Core mail client contract definitions and factory placeholder."""

from abc import ABC, abstractmethod

from task_client_api.task import Task
from task_client_api.tasklist import TaskList

__all__ = ["Client", "get_client"]


class Client(ABC):
    """Abstract base class representing a task client for task operations."""

    """   TASKLIST OPERATIONS   """

    @abstractmethod
    def delete_tasklist(self, tasklist_id: str) -> bool:
        """Delete a tasklist by ..."""
        raise NotImplementedError

    @abstractmethod
    def insert_tasklist(self, tasklist: TaskList) -> TaskList:
        """Insert a tasklist by ..."""
        raise NotImplementedError

    @abstractmethod
    def list_tasklists(self) -> list[TaskList]:
        """List all tasklists."""
        raise NotImplementedError

    """   TASK OPERATIONS   """

    def list_tasks(self, tasklist_id: str) -> list[Task]:
        """List all tasks in a tasklist."""
        raise NotImplementedError

    @abstractmethod
    def insert_task(self, tasklist_id: str, task: Task) -> Task:
        """Insert a task into a tasklist."""
        raise NotImplementedError

    @abstractmethod
    def delete_task(self, tasklist_id: str, task_id: str) -> bool:
        """Delete a task by ..."""
        raise NotImplementedError

    @abstractmethod
    def get_task(self, tasklist_id: str, task_id: str) -> Task:
        """Get a task by its ID."""
        raise NotImplementedError


def get_client(*, interactive: bool = False) -> Client:
    """Return an instance of a Mail Client."""
    raise NotImplementedError
