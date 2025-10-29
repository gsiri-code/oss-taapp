"""Task Contract - Core task representation."""

from abc import ABC, abstractmethod
from enum import Enum


class TaskStatus(Enum):
    NEEDS_ACTION = "needsAction"
    COMPLETED = "completed"


class Task(ABC):
    """Abstract base class representing a google task."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Return the unique identifier of the task."""
        raise NotImplementedError

    @property
    @abstractmethod
    def title(self) -> str:
        """Return title of the task."""
        raise NotImplementedError

    @property
    @abstractmethod
    def status(self) -> TaskStatus:
        """Return status of the task."""
        raise NotImplementedError

    @property
    @abstractmethod
    def due(self) -> str | None:
        """Return of due date the task."""
        raise NotImplementedError

    @property
    @abstractmethod
    def completed(self) -> str | None:
        """Return completion date of the task, ommitted if task incomplete."""
        raise NotImplementedError

    @property
    @abstractmethod
    def deleted(self) -> bool:
        """Return bool if task is deleted."""
        raise NotImplementedError

    @property
    @abstractmethod
    def hidden(self) -> bool:
        """Return bool if task is hidden."""
        raise NotImplementedError
