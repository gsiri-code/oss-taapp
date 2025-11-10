"""Integration tests for the adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, create_autospec

import pytest
from starlette.testclient import TestClient
from task_client_adapter.service_client_adapter import ServiceClientAdapter

import gtask_client_impl
import task_client_api
from task_client_api import Client, Task
from task_client_service import app as service_app
from task_client_service import get_task_client
from task_client_service_client import Client as ServiceClient

# Import classes and helper function from conftest (fixtures are automatically available via pytest)
from .conftest import (
    DummyTask,
    DummyTaskList,
    MockServiceContext,
    _register_adapter_implementations,
)


@pytest.fixture(autouse=True)
def setup_adapter_dependency_injection() -> None:
    """Set up adapter dependency injection for each test in this file."""
    _register_adapter_implementations()


@pytest.mark.integration
@pytest.mark.local_credentials
def test_adapter_exercises_service_and_task_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that the adapter exercises the service and task client."""
    mock_client = create_autospec(Client, spec_set=True)

    # Create a default tasklist (first in list - cannot be deleted)
    default_tasklist = DummyTaskList(
        "default_tl",
        "Default TaskList",
    )

    # Create the tasklist we'll insert and delete
    dummy_tasklist = DummyTaskList(
        "int_tl",
        "Integration Test TaskList",
    )

    dummy_task = DummyTask(
        "int_task",
        "Integration Test Task",
        "int_tl",
        "This is an integration test task body.",
    )

    # Return default tasklist first, then our test tasklist
    # The service prevents deleting the first tasklist (default)
    mock_client.list_tasklists.return_value = [default_tasklist, dummy_tasklist]
    mock_client.insert_tasklist.return_value = dummy_tasklist
    mock_client.delete_tasklist.return_value = True
    mock_client.list_tasks.return_value = [dummy_task]
    mock_client.get_task.return_value = dummy_task
    mock_client.insert_task.return_value = dummy_task
    mock_client.delete_task.return_value = True

    # Ensure the app's lifespan doesn't try to create a real client
    monkeypatch.setattr(
        task_client_api, "get_client", lambda: mock_client, raising=True
    )

    # Force the FastAPI dependency to use our mock client
    service_app.dependency_overrides[get_task_client] = lambda: mock_client  # type: ignore[assignment]

    try:
        base_url = "http://testserver"
        with TestClient(service_app, base_url=base_url) as httpx_client:
            # Create service client and adapter - all calls go through adapter
            service_client = ServiceClient(base_url=base_url)
            service_client.set_httpx_client(httpx_client)
            adapter = ServiceClientAdapter(service_client)

            # Test tasklist operations via adapter -> service -> mock client
            got_tasklists = adapter.list_tasklists()
            # Should return both default and our test tasklist
            assert len(got_tasklists) >= 1
            # Find our test tasklist in the results
            test_tasklist = next(
                (tl for tl in got_tasklists if tl.id == dummy_tasklist.id), None
            )
            assert test_tasklist is not None
            assert test_tasklist.id == dummy_tasklist.id
            assert test_tasklist.title == dummy_tasklist.title

            inserted_tasklist = adapter.insert_tasklist(dummy_tasklist)
            assert inserted_tasklist.id == dummy_tasklist.id
            assert inserted_tasklist.title == dummy_tasklist.title

            # Test task operations via adapter -> service -> mock client
            got_tasks = adapter.list_tasks(dummy_tasklist.id)
            assert len(got_tasks) == 1
            assert got_tasks[0].id == dummy_task.id
            assert got_tasks[0].title == dummy_task.title

            got_one: Task = adapter.get_task(dummy_tasklist.id, dummy_task.id)
            assert got_one.id == dummy_task.id
            assert got_one.title == dummy_task.title

            inserted_task = adapter.insert_task(dummy_tasklist.id, dummy_task)
            assert inserted_task.id == dummy_task.id
            assert inserted_task.title == dummy_task.title

            # Test delete operations via adapter -> service -> mock client
            delete_tasklist_success = adapter.delete_tasklist(dummy_tasklist.id)
            assert delete_tasklist_success is True

            delete_task_success = adapter.delete_task(dummy_tasklist.id, dummy_task.id)
            assert delete_task_success is True

            # Verify all calls went through adapter -> service -> mock client
            # Note: list_tasklists is called twice - once by our test, once by delete_tasklist
            # to check if the tasklist is the default (first in list)
            assert mock_client.list_tasklists.call_count >= 1

            # Note: insert_tasklist receives a TaskList object from the service (which converts
            # the request body), not the original DummyTaskList. Use ANY to allow any TaskList.
            mock_client.insert_tasklist.assert_called_once()
            # Verify it was called with a TaskList that has the correct title
            call_args = mock_client.insert_tasklist.call_args
            assert call_args is not None
            assert (
                len(call_args[0]) == 1
            ), "insert_tasklist should be called with one TaskList argument"
            inserted_tasklist = call_args[0][0]
            assert inserted_tasklist.title == dummy_tasklist.title

            mock_client.list_tasks.assert_called_once_with(dummy_tasklist.id)
            mock_client.get_task.assert_called_once_with(
                dummy_tasklist.id, dummy_task.id
            )

            # Note: insert_task receives a Task object from the service (which converts
            # the request body), not the original DummyTask. Use ANY to allow any Task.
            mock_client.insert_task.assert_called_once()
            # Verify it was called with correct tasklist_id and a Task with correct title
            insert_task_call_args = mock_client.insert_task.call_args
            assert insert_task_call_args is not None
            assert (
                insert_task_call_args[0][0] == dummy_tasklist.id
            ), "First arg should be tasklist_id"
            inserted_task = insert_task_call_args[0][1]
            assert inserted_task.title == dummy_task.title

            mock_client.delete_tasklist.assert_called_once_with(dummy_tasklist.id)
            mock_client.delete_task.assert_called_once_with(
                dummy_tasklist.id, dummy_task.id
            )
    finally:
        service_app.dependency_overrides.pop(get_task_client, None)


@pytest.mark.integration
@pytest.mark.local_credentials
def test_end_to_end_service_call_with_mocked_gtask_impl_and_fastapi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that verifies end-to-end service call with all layers connected.

    This test verifies:
    1. task_client_adapter calls the running task_client_service (via HTTP)
    2. task_client_service calls the mocked gtask_client_impl
    3. All layers are connected correctly and data flows through them

    Flow: adapter -> service (HTTP) -> mocked gtask_client_impl
    """
    mock_tasklist_data = {
        "id": "circleci_tl_123",
        "title": "CircleCI End-to-End Test TaskList",
        "etag": "etag-123",
        "updated": "2025-10-04T14:30:00Z",
        "self_link": "https://tasks.googleapis.com/tasks/v1/lists/circleci_tl_123",
    }

    mock_task_data = {
        "id": "circleci_task_123",
        "title": "CircleCI End-to-End Test Task",
        "tasklist_id": "circleci_tl_123",
        "notes": "This task tests the full integration stack in CI.",
        "status": "needsAction",
        "due": None,
        "completed": None,
        "deleted": False,
        "hidden": False,
    }

    # Create a default tasklist (first in list - cannot be deleted)
    default_tasklist = MagicMock()
    default_tasklist.id = "default_tl"
    default_tasklist.title = "Default TaskList"
    default_tasklist.etag = "etag-default"
    default_tasklist.updated = "2025-01-01T00:00:00Z"
    default_tasklist.self_link = (
        "https://tasks.googleapis.com/tasks/v1/lists/default_tl"
    )

    mock_tasklist = MagicMock()
    mock_tasklist.id = mock_tasklist_data["id"]
    mock_tasklist.title = mock_tasklist_data["title"]
    mock_tasklist.etag = mock_tasklist_data["etag"]
    mock_tasklist.updated = mock_tasklist_data["updated"]
    mock_tasklist.self_link = mock_tasklist_data["self_link"]

    mock_task = MagicMock()
    mock_task.id = mock_task_data["id"]
    mock_task.title = mock_task_data["title"]
    mock_task.notes = mock_task_data["notes"]
    mock_task.status = mock_task_data["status"]
    mock_task.due = mock_task_data["due"]
    mock_task.completed = mock_task_data["completed"]
    mock_task.deleted = mock_task_data["deleted"]
    mock_task.hidden = mock_task_data["hidden"]

    # Step 2: Create mocked gtask_client_impl that the service will call
    # Return default tasklist first, then our test tasklist
    # The service prevents deleting the first tasklist (default)
    mock_gtask_client = MagicMock(spec=gtask_client_impl.GTaskClient)
    mock_gtask_client.list_tasklists.return_value = [default_tasklist, mock_tasklist]
    mock_gtask_client.insert_tasklist.return_value = mock_tasklist
    mock_gtask_client.delete_tasklist.return_value = True
    mock_gtask_client.list_tasks.return_value = [mock_task]
    mock_gtask_client.get_task.return_value = mock_task
    mock_gtask_client.insert_task.return_value = mock_task
    mock_gtask_client.delete_task.return_value = True

    # Configure service to use mocked gtask_client_impl instead of real one
    # This ensures the service calls our mock when get_task_client() is invoked
    monkeypatch.setattr(
        task_client_api,
        "get_client",
        lambda: mock_gtask_client,
        raising=True,
    )

    # Override FastAPI dependency to inject mocked gtask_client_impl into service
    service_app.dependency_overrides[get_task_client] = lambda: mock_gtask_client  # type: ignore[assignment]

    try:
        # Step 1: Start the task_client_service using TestClient
        # NOTE: TestClient is an in-process test client that simulates HTTP requests
        # without starting a real HTTP server. It exercises the full FastAPI application
        # stack (routes, dependencies, middleware, serialization) while being faster
        # and more reliable than a real server. This is the standard approach for
        # integration testing and validates that all layers are connected correctly.
        base_url = "http://testserver"
        with TestClient(service_app, base_url=base_url) as httpx_client:
            # Create task_client_adapter that will call the service
            # The adapter uses the httpx_client which routes through the TestClient,
            # ensuring the adapter -> service -> gtask_client_impl flow is tested
            service_client = ServiceClient(base_url=base_url)
            service_client.set_httpx_client(httpx_client)
            adapter = ServiceClientAdapter(service_client)

            # Tasklist operations via adapter -> service -> mocked gtask_client_impl
            retrieved_tasklists = adapter.list_tasklists()
            # Should return both default and our test tasklist
            assert len(retrieved_tasklists) >= 1
            # Find our test tasklist in the results
            test_tasklist = next(
                (tl for tl in retrieved_tasklists if tl.id == mock_tasklist_data["id"]),
                None,
            )
            assert test_tasklist is not None
            assert test_tasklist.id == mock_tasklist_data["id"]
            assert test_tasklist.title == mock_tasklist_data["title"]

            inserted_tasklist = adapter.insert_tasklist(mock_tasklist)
            assert inserted_tasklist.id == mock_tasklist_data["id"]
            assert inserted_tasklist.title == mock_tasklist_data["title"]

            # Task operations via adapter -> service -> mocked gtask_client_impl
            retrieved_tasks = adapter.list_tasks(mock_tasklist_data["id"])
            assert len(retrieved_tasks) == 1
            first_task = retrieved_tasks[0]
            assert first_task.id == mock_task_data["id"]
            assert first_task.title == mock_task_data["title"]

            retrieved_task = adapter.get_task(
                mock_tasklist_data["id"], mock_task_data["id"]
            )
            assert retrieved_task.id == mock_task_data["id"]
            assert retrieved_task.title == mock_task_data["title"]
            assert retrieved_task.notes == mock_task_data["notes"]

            inserted_task = adapter.insert_task(mock_tasklist_data["id"], mock_task)
            assert inserted_task.id == mock_task_data["id"]
            assert inserted_task.title == mock_task_data["title"]

            # Delete operations via adapter -> service -> mocked gtask_client_impl
            assert adapter.delete_tasklist(mock_tasklist_data["id"]) is True
            assert (
                adapter.delete_task(mock_tasklist_data["id"], mock_task_data["id"])
                is True
            )

            # Step 3: Verify all layers are connected correctly
            # If the mock was called, it proves:
            # - Adapter successfully called the service (layer 1 -> layer 2)
            # - Service successfully called the mocked gtask_client_impl (layer 2 -> layer 3)
            # - All layers are properly connected
            mock_gtask_client.list_tasklists.assert_called()
            mock_gtask_client.insert_tasklist.assert_called()
            mock_gtask_client.delete_tasklist.assert_called_with(
                mock_tasklist_data["id"]
            )
            mock_gtask_client.list_tasks.assert_called_with(mock_tasklist_data["id"])
            mock_gtask_client.get_task.assert_called_with(
                mock_tasklist_data["id"], mock_task_data["id"]
            )
            mock_gtask_client.insert_task.assert_called()
            mock_gtask_client.delete_task.assert_called_with(
                mock_tasklist_data["id"], mock_task_data["id"]
            )
    finally:
        service_app.dependency_overrides.pop(get_task_client, None)


@pytest.mark.integration
@pytest.mark.local_credentials
def test_adapter_with_running_service_and_mock_gtask_client(
    running_service_with_mock_client: MockServiceContext,
) -> None:
    """Test adapter with a running FastAPI service using a mock GTask client.

    All operations go through: adapter -> service -> mocked gtask_client_impl
    """
    # Create the service client and adapter - all calls go through adapter
    service_client = ServiceClient(base_url=running_service_with_mock_client.base_url)
    service_client.set_httpx_client(running_service_with_mock_client.httpx_client)
    adapter = ServiceClientAdapter(service_client)

    # Test GET tasklists via adapter -> service -> mock client
    tasklists = adapter.list_tasklists()
    # Should return both default and our test tasklist
    assert len(tasklists) >= 1
    # Find our test tasklist in the results
    test_tasklist = next(
        (
            tl
            for tl in tasklists
            if tl.id == running_service_with_mock_client.mock_tasklist_data["id"]
        ),
        None,
    )
    assert test_tasklist is not None
    assert test_tasklist.id == running_service_with_mock_client.mock_tasklist_data["id"]
    assert (
        test_tasklist.title
        == running_service_with_mock_client.mock_tasklist_data["title"]
    )
    assert (
        test_tasklist.etag
        == running_service_with_mock_client.mock_tasklist_data["etag"]
    )
    assert (
        test_tasklist.updated
        == running_service_with_mock_client.mock_tasklist_data["updated"]
    )
    assert (
        test_tasklist.self_link
        == running_service_with_mock_client.mock_tasklist_data["self_link"]
    )

    # Verify call went through adapter -> service -> mock client
    running_service_with_mock_client.mock_client.list_tasklists.assert_called_once()

    # Test INSERT tasklist via adapter -> service -> mock client
    mock_tasklist_obj = MagicMock()
    mock_tasklist_obj.id = running_service_with_mock_client.mock_tasklist_data["id"]
    mock_tasklist_obj.title = running_service_with_mock_client.mock_tasklist_data[
        "title"
    ]
    mock_tasklist_obj.etag = running_service_with_mock_client.mock_tasklist_data["etag"]
    mock_tasklist_obj.updated = running_service_with_mock_client.mock_tasklist_data[
        "updated"
    ]
    mock_tasklist_obj.self_link = running_service_with_mock_client.mock_tasklist_data[
        "self_link"
    ]

    inserted_tasklist = adapter.insert_tasklist(mock_tasklist_obj)
    assert (
        inserted_tasklist.id
        == running_service_with_mock_client.mock_tasklist_data["id"]
    )
    assert (
        inserted_tasklist.title
        == running_service_with_mock_client.mock_tasklist_data["title"]
    )

    # Verify call went through adapter -> service -> mock client
    running_service_with_mock_client.mock_client.insert_tasklist.assert_called()

    # Test GET tasks via adapter -> service -> mock client
    tasks = adapter.list_tasks(
        running_service_with_mock_client.mock_tasklist_data["id"]
    )
    assert len(tasks) == 1
    first_task = tasks[0]
    assert first_task.id == running_service_with_mock_client.mock_task_data["id"]
    assert first_task.title == running_service_with_mock_client.mock_task_data["title"]
    assert first_task.notes == running_service_with_mock_client.mock_task_data["notes"]
    assert (
        first_task.status == running_service_with_mock_client.mock_task_data["status"]
    )

    # Verify call went through adapter -> service -> mock client
    running_service_with_mock_client.mock_client.list_tasks.assert_called_once_with(
        running_service_with_mock_client.mock_tasklist_data["id"]
    )

    # Test GET specific task via adapter -> service -> mock client
    retrieved_task = adapter.get_task(
        running_service_with_mock_client.mock_tasklist_data["id"],
        running_service_with_mock_client.mock_task_data["id"],
    )
    assert retrieved_task.id == running_service_with_mock_client.mock_task_data["id"]
    assert (
        retrieved_task.title == running_service_with_mock_client.mock_task_data["title"]
    )
    assert (
        retrieved_task.notes == running_service_with_mock_client.mock_task_data["notes"]
    )
    assert (
        retrieved_task.status
        == running_service_with_mock_client.mock_task_data["status"]
    )

    # Verify call went through adapter -> service -> mock client
    running_service_with_mock_client.mock_client.get_task.assert_called_once_with(
        running_service_with_mock_client.mock_tasklist_data["id"],
        running_service_with_mock_client.mock_task_data["id"],
    )

    # Test DELETE tasklist via adapter -> service -> mock client
    delete_success = adapter.delete_tasklist(
        running_service_with_mock_client.mock_tasklist_data["id"]
    )
    assert delete_success is True

    # Verify call went through adapter -> service -> mock client
    running_service_with_mock_client.mock_client.delete_tasklist.assert_called_once_with(
        running_service_with_mock_client.mock_tasklist_data["id"]
    )

    # Test DELETE task via adapter -> service -> mock client
    delete_task_success = adapter.delete_task(
        running_service_with_mock_client.mock_tasklist_data["id"],
        running_service_with_mock_client.mock_task_data["id"],
    )
    assert delete_task_success is True

    # Verify call went through adapter -> service -> mock client
    running_service_with_mock_client.mock_client.delete_task.assert_called_once_with(
        running_service_with_mock_client.mock_tasklist_data["id"],
        running_service_with_mock_client.mock_task_data["id"],
    )


@pytest.mark.integration
@pytest.mark.local_credentials
def test_verify_mock_gtask_client_isolation(
    running_service_with_mock_client: MockServiceContext,
) -> None:
    """Verify that we are NEVER using the real GTask client.

    All operations go through: adapter -> service -> mocked gtask_client_impl
    """
    # Create the service client and adapter - all calls go through adapter
    service_client = ServiceClient(base_url=running_service_with_mock_client.base_url)
    service_client.set_httpx_client(running_service_with_mock_client.httpx_client)
    adapter = ServiceClientAdapter(service_client)

    # Test that we get our mock data via adapter -> service -> mock client
    tasklists = adapter.list_tasklists()
    # Should return both default and our test tasklist
    assert len(tasklists) >= 1

    # Find our test tasklist in the results
    tasklist = next(
        (tl for tl in tasklists if tl.id == "test_tl_123"),
        None,
    )
    assert tasklist is not None

    # Verify we're getting our mock data, not real Google Tasks data
    assert tasklist.id == "test_tl_123"  # Our mock ID
    assert tasklist.title == "Test Integration TaskList"  # Our mock title

    # Test that invalid IDs raise RuntimeError via adapter -> service -> mock client
    with pytest.raises(RuntimeError, match="Task with ID invalid-task-id not found"):
        adapter.get_task("test_tl_123", "invalid-task-id")

    # Verify calls went through adapter -> service -> mock client
    running_service_with_mock_client.mock_client.list_tasklists.assert_called_once()
    running_service_with_mock_client.mock_client.get_task.assert_called_once_with(
        "test_tl_123", "invalid-task-id"
    )
