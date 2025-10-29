"""Task List Contract - Core task list representation."""

from abc import ABC, abstractmethod

class TaskList(ABC):
    """Abstract base class representing a google task list."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Return the unique identifier of the task list."""
        raise NotImplementedError

    @property
    @abstractmethod
    def title(self) -> str:
        """Return title of the task list."""
        raise NotImplementedError