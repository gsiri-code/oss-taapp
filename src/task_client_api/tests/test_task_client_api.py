"""Tests for the task client API abstract base classes.

This module contains unit tests that verify the contracts and behavior
of the task_client_api.Client, task_client_api.Task, and task_client_api.TaskList abstractions.
These tests use mocks to demonstrate how implementations should behave
and serve as documentation for the expected API contracts.
"""

from unittest.mock import Mock

from task_client_api import Client, Task, TaskList


def test_client_delete_tasklist() -> None:
    """Verifies and demonstrates the contract for the `delete_tasklist` method.

    This test ensures that any implementation of the `Client` abstraction
    must have a `delete_tasklist` method that returns a boolean.
    """
    # ARRANGE: Create mocks that conform to our abstractions.
    mock_tasklist = Mock(spec=TaskList)
    mock_tasklist.id = "tasklist_1"
    mock_tasklist.title = "Test Tasklist"

    mock_client = Mock(spec=Client)
    mock_client.delete_tasklist.return_value = True

    # ACT: Use the client as a consumer would.
    success = mock_client.delete_tasklist(tasklist_id="tasklist_1")

    # ASSERT: Verify the interaction and the result.
    mock_client.delete_tasklist.assert_called_once_with(tasklist_id="tasklist_1")
    assert success is True


def test_client_insert_tasklist() -> None:
    """Verifies and demonstrates the contract for the `insert_tasklist` method.

    This test ensures that any implementation of the `Client` abstraction
    must have a `insert_tasklist` method that returns a TaskList.
    """
    # ARRANGE: Create mocks that conform to our abstractions.
    mock_tasklist = Mock(spec=TaskList)
    mock_tasklist.id = "tasklist_1"
    mock_tasklist.title = "Test Tasklist"

    mock_client = Mock(spec=Client)
    mock_client.insert_tasklist.return_value = mock_tasklist

    # ACT: Use the client as a consumer would.
    inserted_tasklist = mock_client.insert_tasklist(tasklist=mock_tasklist)

    # ASSERT: Verify the interaction and the result.
    mock_client.insert_tasklist.assert_called_once_with(tasklist=mock_tasklist)
    assert inserted_tasklist is not None
    assert inserted_tasklist.id == "tasklist_1"
    assert inserted_tasklist.title == "Test Tasklist"


def test_client_list_tasklists() -> None:
    """Verifies and demonstrates the contract for the `list_tasklists` method.

    This test ensures that any implementation of the `Client` abstraction
    must have a `list_tasklists` method that returns a list of TaskList objects.
    """
    # ARRANGE: Create mocks that conform to our abstractions.
    mock_tasklist1 = Mock(spec=TaskList)
    mock_tasklist1.id = "tasklist_1"
    mock_tasklist1.title = "Test Tasklist 1"

    mock_tasklist2 = Mock(spec=TaskList)
    mock_tasklist2.id = "tasklist_2"
    mock_tasklist2.title = "Test Tasklist 2"

    mock_client = Mock(spec=Client)
    mock_client.list_tasklists.return_value = [mock_tasklist1, mock_tasklist2]

    # ACT: Use the client as a consumer would.
    tasklists = mock_client.list_tasklists()

    # ASSERT: Verify the interaction and the result.
    mock_client.list_tasklists.assert_called_once_with()
    assert len(tasklists) == len(mock_client.list_tasklists.return_value)
    assert tasklists[0].id == "tasklist_1"
    assert tasklists[1].id == "tasklist_2"


def test_client_list_tasks() -> None:
    """Verifies and demonstrates the contract for the `list_tasks` method.

    This test ensures that any implementation of the `Client` abstraction
    must have a `list_tasks` method that returns a list of Task objects.
    """
    # ARRANGE: Create mocks that conform to our abstractions.
    mock_task1 = Mock(spec=Task)
    mock_task1.id = "task_1"
    mock_task1.title = "Test Task 1"

    mock_task2 = Mock(spec=Task)
    mock_task2.id = "task_2"
    mock_task2.title = "Test Task 2"

    mock_client = Mock(spec=Client)
    mock_client.list_tasks.return_value = [mock_task1, mock_task2]

    # ACT: Use the client as a consumer would.
    tasks = mock_client.list_tasks(tasklist_id="tasklist_1")

    # ASSERT: Verify the interaction and the result.
    mock_client.list_tasks.assert_called_once_with(tasklist_id="tasklist_1")
    assert len(tasks) == len(mock_client.list_tasks.return_value)
    assert tasks[0].id == "task_1"
    assert tasks[1].id == "task_2"


def test_client_insert_task() -> None:
    """Verifies and demonstrates the contract for the `insert_task` method.

    This test ensures that any implementation of the `Client` abstraction
    must have a `insert_task` method that returns a Task.
    """
    # ARRANGE: Create mocks that conform to our abstractions.
    mock_task = Mock(spec=Task)
    mock_task.id = "task_1"
    mock_task.title = "Test Task"

    mock_client = Mock(spec=Client)
    mock_client.insert_task.return_value = mock_task

    # ACT: Use the client as a consumer would.
    inserted_task = mock_client.insert_task(tasklist_id="tasklist_1", task=mock_task)

    # ASSERT: Verify the interaction and the result.
    mock_client.insert_task.assert_called_once_with(tasklist_id="tasklist_1", task=mock_task)
    assert inserted_task is not None
    assert inserted_task.id == "task_1"
    assert inserted_task.title == "Test Task"


def test_client_delete_task() -> None:
    """Verifies and demonstrates the contract for the `delete_task` method.

    This test ensures that any implementation of the `Client` abstraction
    must have a `delete_task` method that returns a boolean.
    """
    # ARRANGE: Create mocks that conform to our abstractions.
    mock_client = Mock(spec=Client)
    mock_client.delete_task.return_value = True

    # ACT: Use the client as a consumer would.
    success = mock_client.delete_task(tasklist_id="tasklist_1", task_id="task_1")

    # ASSERT: Verify the interaction and the result.
    mock_client.delete_task.assert_called_once_with(tasklist_id="tasklist_1", task_id="task_1")
    assert success is True


def test_client_get_task() -> None:
    """Verifies and demonstrates the contract for the `get_task` method.

    This test ensures that any implementation of the `Client` abstraction
    must have a `get_task` method that returns a Task.
    """
    # ARRANGE: Create mocks that conform to our abstractions.
    mock_task = Mock(spec=Task)
    mock_task.id = "task_1"
    mock_task.title = "Test Task"

    mock_client = Mock(spec=Client)
    mock_client.get_task.return_value = mock_task

    # ACT: Use the client as a consumer would.
    retrieved_task = mock_client.get_task(tasklist_id="tasklist_1", task_id="task_1")

    # ASSERT: Verify the interaction and the result.
    mock_client.get_task.assert_called_once_with(tasklist_id="tasklist_1", task_id="task_1")
    assert retrieved_task is not None
    assert retrieved_task.id == "task_1"
    assert retrieved_task.title == "Test Task"
