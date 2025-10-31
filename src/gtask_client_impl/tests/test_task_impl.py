"""Tests for GTask implementation colocated with GTaskClient."""

import json

from gtask_client_impl.task_impl import GTask


class TestGTask:
    """Test cases for the GTask class."""

    def test_basic_task_creation(self) -> None:
        """Test creating a GTask with valid data."""
        task_data = {
            "id": "task123",
            "title": "Test Task",
            "notes": "This is a test task",
            "status": "needsAction",
            "due": "2025-07-30T10:30:00Z",
            "completed": None,
            "deleted": False,
            "hidden": False,
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.id == "task123"
        assert task.title == "Test Task"
        assert task.notes == "This is a test task"
        assert task.status == "needsAction"
        assert task.due == "2025-07-30T10:30:00Z"
        assert task.completed is None
        assert task.deleted is False
        assert task.hidden is False

    def test_task_with_minimal_data(self) -> None:
        """Test task with only required fields (title)."""
        task_data = {
            "id": "minimal123",
            "title": "Minimal Task",
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.id == "minimal123"
        assert task.title == "Minimal Task"
        assert task.notes is None
        assert task.status == "needsAction"  # Default value
        assert task.due is None
        assert task.completed is None
        assert task.deleted is False  # Default value
        assert task.hidden is False  # Default value

    def test_task_with_all_optional_fields(self) -> None:
        """Test task with all optional fields populated."""
        task_data = {
            "id": "full123",
            "title": "Complete Task",
            "notes": "Detailed notes about the task",
            "status": "completed",
            "due": "2025-07-30T10:30:00Z",
            "completed": "2025-07-29T15:45:00Z",
            "deleted": False,
            "hidden": True,
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.id == "full123"
        assert task.title == "Complete Task"
        assert task.notes == "Detailed notes about the task"
        assert task.status == "completed"
        assert task.due == "2025-07-30T10:30:00Z"
        assert task.completed == "2025-07-29T15:45:00Z"
        assert task.deleted is False
        assert task.hidden is True

    def test_task_with_completed_status(self) -> None:
        """Test task with completed status."""
        task_data = {
            "id": "completed123",
            "title": "Completed Task",
            "status": "completed",
            "completed": "2025-07-30T10:30:00Z",
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.status == "completed"
        assert task.completed == "2025-07-30T10:30:00Z"

    def test_task_with_due_date(self) -> None:
        """Test task with due date (RFC 3339 timestamp)."""
        task_data = {
            "id": "duedate123",
            "title": "Task with Due Date",
            "due": "2025-08-15T23:59:59Z",
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.due == "2025-08-15T23:59:59Z"

    def test_task_with_notes(self) -> None:
        """Test task with notes field."""
        task_data = {
            "id": "notes123",
            "title": "Task with Notes",
            "notes": "Important reminder: Don't forget to follow up",
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.notes == "Important reminder: Don't forget to follow up"

    def test_task_with_deleted_flag(self) -> None:
        """Test task with deleted flag set to True."""
        task_data = {
            "id": "deleted123",
            "title": "Deleted Task",
            "deleted": True,
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.deleted is True

    def test_task_with_hidden_flag(self) -> None:
        """Test task with hidden flag set to True."""
        task_data = {
            "id": "hidden123",
            "title": "Hidden Task",
            "hidden": True,
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.hidden is True

    def test_task_with_empty_strings(self) -> None:
        """Test task with empty string values."""
        task_data = {
            "id": "",
            "title": "",
            "notes": "",
            "status": "",
        }

        raw_data = json.dumps(task_data)
        task = GTask(raw_data=raw_data)

        assert task.id == ""
        assert task.title == ""
        assert task.notes == ""
        assert task.status == ""
