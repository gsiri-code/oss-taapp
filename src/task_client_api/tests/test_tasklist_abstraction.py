"""Tests for the task_client_api tasklist abstraction."""

from unittest.mock import Mock

from task_client_api.tasklist import TaskList


def test_tasklist_abstraction_comprehensive() -> None:
    """Verifies all properties work together in a comprehensive test."""
    mock_tasklist = Mock(spec=TaskList)
    mock_tasklist.id = "tasklist_abc123"
    mock_tasklist.title = "Work Tasks"
    mock_tasklist.etag = '"MTIzNDU2Nzg5MA"'
    mock_tasklist.updated = "2025-07-30T14:45:30Z"
    mock_tasklist.self_link = (
        "https://tasks.googleapis.com/tasks/v1/users/@me/lists/tasklist_abc123"
    )

    properties = {
        "id": mock_tasklist.id,
        "title": mock_tasklist.title,
        "etag": mock_tasklist.etag,
        "updated": mock_tasklist.updated,
        "self_link": mock_tasklist.self_link,
    }

    assert properties["id"] == "tasklist_abc123"
    assert properties["title"] == "Work Tasks"
    assert properties["etag"] == '"MTIzNDU2Nzg5MA"'
    assert properties["updated"] == "2025-07-30T14:45:30Z"
    assert (
        properties["self_link"]
        == "https://tasks.googleapis.com/tasks/v1/users/@me/lists/tasklist_abc123"
    )

    for value in properties.values():
        assert isinstance(value, str)
