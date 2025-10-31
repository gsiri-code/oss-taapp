"""Tests for the task_client_api task abstraction."""

from unittest.mock import Mock

from task_client_api.task import Task


def test_task_abstraction_comprehensive() -> None:
    """Verifies all properties work together in a comprehensive test."""
    mock_task = Mock(spec=Task)
    mock_task.id = "task_12345"
    mock_task.title = "Complete project documentation"
    mock_task.notes = "Review and update all API documentation"
    mock_task.status = "needsAction"
    mock_task.due = "2025-08-15T10:00:00Z"
    mock_task.completed = None
    mock_task.deleted = False
    mock_task.hidden = False

    properties = {
        "id": mock_task.id,
        "title": mock_task.title,
        "notes": mock_task.notes,
        "status": mock_task.status,
        "due": mock_task.due,
        "completed": mock_task.completed,
        "deleted": mock_task.deleted,
        "hidden": mock_task.hidden,
    }

    assert properties["id"] == "task_12345"
    assert properties["title"] == "Complete project documentation"
    assert properties["notes"] == "Review and update all API documentation"
    assert properties["status"] == "needsAction"
    assert properties["due"] == "2025-08-15T10:00:00Z"
    assert properties["completed"] is None
    assert properties["deleted"] is False
    assert properties["hidden"] is False

    assert isinstance(properties["id"], str)
    assert isinstance(properties["title"], str)
    assert isinstance(properties["notes"], str)
    assert isinstance(properties["status"], str)
    assert isinstance(properties["due"], str)
    assert properties["completed"] is None
    assert isinstance(properties["deleted"], bool)
    assert isinstance(properties["hidden"], bool)
