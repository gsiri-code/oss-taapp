"""Integration tests for the adapter."""

from __future__ import annotations

import socket
import time
from contextlib import closing
from dataclasses import dataclass
from unittest.mock import MagicMock, create_autospec

import pytest
from mail_client_adapter.service_client_adapter import ServiceClientAdapter
from starlette.testclient import TestClient

import gmail_client_impl
import mail_client_api
from mail_client_api import Client, Message
from mail_client_service import app as service_app
from mail_client_service import get_mail_client
from mail_client_service_client import Client as ServiceClient


@pytest.fixture(autouse=True)
def setup_adapter_dependency_injection() -> None:
    """Set up adapter dependency injection for each test in this file."""
    # Import and register the adapter implementation
    import mail_client_adapter  # noqa: PLC0415

    mail_client_adapter.register()

    # Also register the service message implementation
    from mail_client_adapter.service_message import register as register_message  # noqa: PLC0415

    register_message()


@dataclass
class MockServiceContext:
    """Context for running service with mock client."""

    base_url: str
    mock_data: dict
    httpx_client: TestClient
    mock_client: Client


class DummyMessage:
    """Dummy message for testing."""

    def __init__(self, message_id: str, sender: str, recipient: str, subject: str, date: str, body: str) -> None:  # noqa: PLR0913
        """Initialize the dummy message."""
        self.id = message_id
        self.from_ = sender
        self.to = recipient
        self.subject = subject
        self.date = date
        self.body = body


def _free_port() -> int:  # same as in e2e tests
    """Find a free port for the test server."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _wait_for_ready(base_url: str, timeout_s: int = 10) -> None:  # same as in e2e but shorter timeout
    """Wait for the service to be ready."""
    import httpx  # noqa: PLC0415 # literally only used in this test

    start = time.time()
    while time.time() - start < timeout_s:
        try:
            r = httpx.get(f"{base_url}/openapi.json", timeout=2.0)
            if r.status_code < 500:  # noqa: PLR2004
                return
        except Exception as e:  # noqa: BLE001
            pytest.log.error(f"Error waiting for service to be ready: {e}")
        time.sleep(0.5)
    msg = f"Service never became ready at {base_url}"
    raise RuntimeError(msg)


@pytest.fixture
def mock_gmail_client() -> tuple[MagicMock, dict[str, str]]:
    """Create a mock Gmail client with test data."""
    mock_message_data = {
        "id": "test_msg_123",
        "from": "sender@test.com",
        "to": "recipient@test.com",
        "subject": "Test Integration Message",
        "date": "2025-01-15T10:30:00Z",
        "body": "This is a test message for integration testing.",
    }

    mock_message = MagicMock()
    mock_message.id = mock_message_data["id"]
    mock_message.from_ = mock_message_data["from"]
    mock_message.to = mock_message_data["to"]
    mock_message.subject = mock_message_data["subject"]
    mock_message.date = mock_message_data["date"]
    mock_message.body = mock_message_data["body"]

    # Create a mock that implements the Client interface
    mock_gmail_client = MagicMock(spec=gmail_client_impl.GmailClient)

    # Configure the mock to return the message for valid ID, raise error for invalid
    def get_message_side_effect(message_id: str) -> Message:
        if message_id == mock_message_data["id"]:
            return mock_message
        msg = f"Message with ID {message_id} not found"
        raise RuntimeError(msg)

    # Configure mark_as_read and delete_message to handle invalid IDs
    def mark_as_read_side_effect(message_id: str) -> bool:
        return message_id == mock_message_data["id"]

    def delete_message_side_effect(message_id: str) -> bool:
        return message_id == mock_message_data["id"]

    # Explicitly configure all required methods
    mock_gmail_client.get_message.side_effect = get_message_side_effect
    mock_gmail_client.get_messages.return_value = [mock_message]
    mock_gmail_client.mark_as_read.side_effect = mark_as_read_side_effect
    mock_gmail_client.delete_message.side_effect = delete_message_side_effect

    # Ensure all methods exist and are callable
    assert hasattr(mock_gmail_client, "get_message"), "Mock missing get_message method"
    assert hasattr(mock_gmail_client, "get_messages"), "Mock missing get_messages method"
    assert hasattr(mock_gmail_client, "mark_as_read"), "Mock missing mark_as_read method"
    assert hasattr(mock_gmail_client, "delete_message"), "Mock missing delete_message method"

    return mock_gmail_client, mock_message_data


@pytest.fixture
def running_service_with_mock_client(
    mock_gmail_client: tuple[MagicMock, dict[str, str]], monkeypatch: pytest.MonkeyPatch
) -> MockServiceContext:
    """Start a FastAPI service with a mocked Gmail client."""
    mock_client, mock_data = mock_gmail_client

    # CRITICAL: Patch the get_client function BEFORE any imports
    # This ensures the real Gmail client is NEVER used
    def mock_get_client(*args, **kwargs) -> MagicMock:  # noqa: ARG001, ANN003, ANN002
        return mock_client

    # Patch the get_client function in mail_client_api
    monkeypatch.setattr(mail_client_api, "get_client", mock_get_client, raising=True)

    # Also patch the GmailClient class itself to prevent instantiation
    monkeypatch.setattr(gmail_client_impl, "GmailClient", lambda *args, **kwargs: mock_client, raising=True)  # noqa: ARG005

    # CRITICAL: Override the FastAPI app's state to use our mock client
    # This bypasses the lifespan function
    service_app.state.mail_client = mock_client

    # Also override the FastAPI dependency to use our mock client
    service_app.dependency_overrides[get_mail_client] = lambda: mock_client  # type: ignore[assignment]

    # Find a free port
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    # Start the service using TestClient instead of subprocess
    # This ensures our dependency overrides work
    try:
        with TestClient(service_app, base_url=base_url) as httpx_client:
            yield MockServiceContext(base_url=base_url, mock_data=mock_data, httpx_client=httpx_client, mock_client=mock_client)
    finally:
        service_app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.local_credentials
def test_adapter_exercises_service_and_mail_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that the adapter exercises the service and mail client."""
    mock_client = create_autospec(Client, spec_set=True)

    dummy = DummyMessage(
        "int_msg",
        "tester@example.com",
        "recipient@example.com",
        "Integration Test",
        "2025-10-03T12:00:00Z",
        "This is an integration test body.",
    )

    mock_client.get_message.return_value = dummy
    mock_client.get_messages.return_value = [dummy]
    mock_client.mark_as_read.return_value = True
    mock_client.delete_message.return_value = True

    # Ensure the app's lifespan doesn't try to create a real client
    monkeypatch.setattr(mail_client_api, "get_client", lambda: mock_client, raising=True)

    # Force the FastAPI dependency to use our mock client
    service_app.dependency_overrides[get_mail_client] = lambda: mock_client  # type: ignore[assignment]

    try:
        base_url = "http://testserver"
        with TestClient(service_app, base_url=base_url) as httpx_client:
            service_client = ServiceClient(base_url=base_url)
            service_client.set_httpx_client(httpx_client)

            adapter = ServiceClientAdapter(service_client)

            got_one: Message = adapter.get_message(dummy.id)
            # Adapter returns an iterator; materialize to a list for assertions
            got_many_iter = adapter.get_messages()
            got_many: list[Message] = list(got_many_iter)

        assert got_one.id == dummy.id
        assert got_one.from_ == dummy.from_
        assert got_one.to == dummy.to
        assert got_one.subject == dummy.subject
        assert got_one.body == dummy.body

        assert isinstance(got_many, list)
        assert len(got_many) == 1
        only = got_many[0]
        assert only.id == dummy.id
        assert only.subject == "Integration Test"

        mock_client.get_message.assert_called_once_with(dummy.id)
        mock_client.get_messages.assert_called_once()
    finally:
        service_app.dependency_overrides.pop(get_mail_client, None)


@pytest.mark.integration
@pytest.mark.local_credentials
def test_end_to_end_service_call_with_mocked_gmail_impl_and_fastapi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end-style integration that wires.

    mail_client_adapter -> mail_client_service -> mocked gmail_client_impl.
    """
    mock_message_data = {
        "id": "circleci_msg_123",
        "from": "sender@circleci.com",
        "to": "recipient@circleci.com",
        "subject": "CircleCI End-to-End Test",
        "date": "2025-10-04T14:30:00Z",
        "body": "This message tests the full integration stack in CI.",
    }

    mock_message = MagicMock()
    mock_message.id = mock_message_data["id"]
    mock_message.from_ = mock_message_data["from"]
    mock_message.to = mock_message_data["to"]
    mock_message.subject = mock_message_data["subject"]
    mock_message.date = mock_message_data["date"]
    mock_message.body = mock_message_data["body"]

    mock_gmail_client = MagicMock(spec=gmail_client_impl.GmailClient)
    mock_gmail_client.get_message.return_value = mock_message
    mock_gmail_client.get_messages.return_value = [mock_message]
    mock_gmail_client.mark_as_read.return_value = True
    mock_gmail_client.delete_message.return_value = True

    # Prevent the app lifespan from creating a real Gmail client
    monkeypatch.setattr(
        mail_client_api,
        "get_client",
        lambda: mock_gmail_client,
        raising=True,
    )

    # Override FastAPI dependency to use the mocked Gmail client
    service_app.dependency_overrides[get_mail_client] = lambda: mock_gmail_client  # type: ignore[assignment]

    try:
        base_url = "http://testserver"
        with TestClient(service_app, base_url=base_url) as httpx_client:
            service_client = ServiceClient(base_url=base_url)
            service_client.set_httpx_client(httpx_client)

            adapter = ServiceClientAdapter(service_client)

            # Single message flow
            retrieved_message = adapter.get_message(mock_message_data["id"])
            assert retrieved_message.id == mock_message_data["id"]
            assert retrieved_message.from_ == mock_message_data["from"]
            assert retrieved_message.to == mock_message_data["to"]
            assert retrieved_message.subject == mock_message_data["subject"]
            assert retrieved_message.date == mock_message_data["date"]
            assert retrieved_message.body == mock_message_data["body"]

            # Messages list flow (adapter returns iterator)
            retrieved_messages = list(adapter.get_messages())
            assert len(retrieved_messages) == 1
            first_message = retrieved_messages[0]
            assert first_message.id == mock_message_data["id"]
            assert first_message.subject == mock_message_data["subject"]

            # Mark-as-read and delete
            assert adapter.mark_as_read(mock_message_data["id"]) is True
            assert adapter.delete_message(mock_message_data["id"]) is True

            # Verify delegation to mocked Gmail client
            mock_gmail_client.get_message.assert_called_with(mock_message_data["id"])
            mock_gmail_client.get_messages.assert_called_once()
            mock_gmail_client.mark_as_read.assert_called_with(mock_message_data["id"])
            mock_gmail_client.delete_message.assert_called_with(mock_message_data["id"])
    finally:
        service_app.dependency_overrides.pop(get_mail_client, None)


@pytest.mark.integration
@pytest.mark.local_credentials
def test_adapter_with_running_service_and_mock_gmail_client(running_service_with_mock_client: MockServiceContext) -> None:
    """Test adapter with a running FastAPI service using a mock Gmail client."""
    # Create the service client and adapter
    service_client = ServiceClient(base_url=running_service_with_mock_client.base_url)
    service_client.set_httpx_client(running_service_with_mock_client.httpx_client)
    adapter = ServiceClientAdapter(service_client)

    # Test GET messages
    messages = list(adapter.get_messages(max_results=5))
    assert len(messages) == 1
    first_message = messages[0]
    assert first_message.id == running_service_with_mock_client.mock_data["id"]
    assert first_message.subject == running_service_with_mock_client.mock_data["subject"]
    assert first_message.from_ == running_service_with_mock_client.mock_data["from"]
    assert first_message.to == running_service_with_mock_client.mock_data["to"]
    assert first_message.date == running_service_with_mock_client.mock_data["date"]
    assert first_message.body == running_service_with_mock_client.mock_data["body"]

    # Verify mock Gmail client was called
    running_service_with_mock_client.mock_client.get_messages.assert_called_once()

    # Test GET specific message
    retrieved_message = adapter.get_message(running_service_with_mock_client.mock_data["id"])
    assert retrieved_message.id == running_service_with_mock_client.mock_data["id"]
    assert retrieved_message.subject == running_service_with_mock_client.mock_data["subject"]
    assert retrieved_message.from_ == running_service_with_mock_client.mock_data["from"]
    assert retrieved_message.to == running_service_with_mock_client.mock_data["to"]
    assert retrieved_message.date == running_service_with_mock_client.mock_data["date"]
    assert retrieved_message.body == running_service_with_mock_client.mock_data["body"]

    # Verify mock Gmail client was called with correct message ID
    running_service_with_mock_client.mock_client.get_message.assert_called_once_with(
        running_service_with_mock_client.mock_data["id"]
    )

    # Test POST mark as read
    mark_success = adapter.mark_as_read(running_service_with_mock_client.mock_data["id"])
    assert mark_success is True

    # Verify mock Gmail client was called with correct message ID
    running_service_with_mock_client.mock_client.mark_as_read.assert_called_once_with(
        running_service_with_mock_client.mock_data["id"]
    )

    # Test DELETE message
    delete_success = adapter.delete_message(running_service_with_mock_client.mock_data["id"])
    assert delete_success is True

    # Verify mock Gmail client was called with correct message ID
    running_service_with_mock_client.mock_client.delete_message.assert_called_once_with(
        running_service_with_mock_client.mock_data["id"]
    )


@pytest.mark.integration
@pytest.mark.local_credentials
def test_adapter_error_handling_with_running_service(running_service_with_mock_client: MockServiceContext) -> None:
    """Test adapter error handling with a running service."""
    # Create the service client and adapter
    service_client = ServiceClient(base_url=running_service_with_mock_client.base_url)
    service_client.set_httpx_client(running_service_with_mock_client.httpx_client)
    adapter = ServiceClientAdapter(service_client)

    # Test with invalid message ID - should raise RuntimeError
    with pytest.raises(RuntimeError, match=r"not found|failed"):
        adapter.get_message("invalid-message-id")

    # Verify mock Gmail client was called with invalid ID
    running_service_with_mock_client.mock_client.get_message.assert_called_once_with("invalid-message-id")

    # Test mark as read with invalid ID - service always returns True
    mark_success = adapter.mark_as_read("invalid-message-id")
    assert mark_success is True  # Service always returns success

    # Verify mock Gmail client was called with invalid ID
    running_service_with_mock_client.mock_client.mark_as_read.assert_called_once_with("invalid-message-id")

    # Test delete with invalid ID - service always returns True
    delete_success = adapter.delete_message("invalid-message-id")
    assert delete_success is True  # Service always returns success

    # Verify mock Gmail client was called with invalid ID
    running_service_with_mock_client.mock_client.delete_message.assert_called_once_with("invalid-message-id")


@pytest.mark.integration
@pytest.mark.local_credentials
def test_adapter_performance_with_running_service(running_service_with_mock_client: MockServiceContext) -> None:
    """Test adapter performance with a running service."""
    # Create the service client and adapter
    service_client = ServiceClient(base_url=running_service_with_mock_client.base_url)
    service_client.set_httpx_client(running_service_with_mock_client.httpx_client)
    adapter = ServiceClientAdapter(service_client)

    # Test multiple operations
    start_time = time.time()

    # Perform multiple get_messages calls
    for _ in range(3):
        messages = list(adapter.get_messages(max_results=1))
        assert len(messages) == 1

    # Perform multiple get_message calls
    for _ in range(3):
        message = adapter.get_message(running_service_with_mock_client.mock_data["id"])
        assert message.id == running_service_with_mock_client.mock_data["id"]

    # Perform multiple mark_as_read calls
    for _ in range(3):
        success = adapter.mark_as_read(running_service_with_mock_client.mock_data["id"])
        assert success is True

    end_time = time.time()
    execution_time = end_time - start_time

    # Should complete within reasonable time (adjust as needed)
    assert execution_time < 5.0, f"Operations took too long: {execution_time:.2f}s"  # noqa: PLR2004 # arbitrary timeout

    # Verify mock Gmail client was called the expected number of times
    EXPECTED_CALL_COUNT = 3  # noqa: N806
    assert running_service_with_mock_client.mock_client.get_messages.call_count == EXPECTED_CALL_COUNT
    assert running_service_with_mock_client.mock_client.get_message.call_count == EXPECTED_CALL_COUNT
    assert running_service_with_mock_client.mock_client.mark_as_read.call_count == EXPECTED_CALL_COUNT


@pytest.mark.integration
@pytest.mark.local_credentials
def test_adapter_comprehensive_operations_with_running_service(running_service_with_mock_client: MockServiceContext) -> None:
    """Test comprehensive adapter operations with a running service."""
    # Create the service client and adapter
    service_client = ServiceClient(base_url=running_service_with_mock_client.base_url)
    service_client.set_httpx_client(running_service_with_mock_client.httpx_client)
    adapter = ServiceClientAdapter(service_client)

    # Test 1: Get messages with different max_results
    for max_results in [1, 5, 10]:
        messages = list(adapter.get_messages(max_results=max_results))
        assert len(messages) == 1  # Our mock only returns 1 message
        assert messages[0].id == running_service_with_mock_client.mock_data["id"]

    # Test 2: Get specific message multiple times
    for _ in range(3):
        message = adapter.get_message(running_service_with_mock_client.mock_data["id"])
        assert message.id == running_service_with_mock_client.mock_data["id"]
        assert message.subject == running_service_with_mock_client.mock_data["subject"]
        assert message.from_ == running_service_with_mock_client.mock_data["from"]
        assert message.to == running_service_with_mock_client.mock_data["to"]
        assert message.date == running_service_with_mock_client.mock_data["date"]
        assert message.body == running_service_with_mock_client.mock_data["body"]

    # Test 3: Mark as read multiple times
    for _ in range(3):
        success = adapter.mark_as_read(running_service_with_mock_client.mock_data["id"])
        assert success is True

    # Test 4: Delete message (this should work with our mock)
    delete_success = adapter.delete_message(running_service_with_mock_client.mock_data["id"])
    assert delete_success is True

    # Verify mock Gmail client was called the expected number of times
    EXPECTED_CALL_COUNT = 3  # noqa: N806
    assert running_service_with_mock_client.mock_client.get_messages.call_count == EXPECTED_CALL_COUNT
    assert running_service_with_mock_client.mock_client.get_message.call_count == EXPECTED_CALL_COUNT
    assert running_service_with_mock_client.mock_client.mark_as_read.call_count == EXPECTED_CALL_COUNT
    assert running_service_with_mock_client.mock_client.delete_message.call_count == 1


@pytest.mark.integration
@pytest.mark.local_credentials
def test_adapter_message_properties_with_running_service(running_service_with_mock_client: MockServiceContext) -> None:
    """Test that adapter returns messages with correct properties."""
    # Create the service client and adapter
    service_client = ServiceClient(base_url=running_service_with_mock_client.base_url)
    service_client.set_httpx_client(running_service_with_mock_client.httpx_client)
    adapter = ServiceClientAdapter(service_client)

    # Get messages and verify properties
    messages = list(adapter.get_messages(max_results=1))
    assert len(messages) == 1

    message = messages[0]

    # Verify all required properties exist and are strings
    assert hasattr(message, "id")
    assert hasattr(message, "subject")
    assert hasattr(message, "from_")
    assert hasattr(message, "to")
    assert hasattr(message, "date")
    assert hasattr(message, "body")

    # Verify property types
    assert isinstance(message.id, str)
    assert isinstance(message.subject, str)
    assert isinstance(message.from_, str)
    assert isinstance(message.to, str)
    assert isinstance(message.date, str)
    assert isinstance(message.body, str)

    # Verify property values match mock data
    assert message.id == running_service_with_mock_client.mock_data["id"]
    assert message.subject == running_service_with_mock_client.mock_data["subject"]
    assert message.from_ == running_service_with_mock_client.mock_data["from"]
    assert message.to == running_service_with_mock_client.mock_data["to"]
    assert message.date == running_service_with_mock_client.mock_data["date"]
    assert message.body == running_service_with_mock_client.mock_data["body"]

    # Verify mock Gmail client was called
    running_service_with_mock_client.mock_client.get_messages.assert_called_once()


@pytest.mark.integration
@pytest.mark.local_credentials
def test_adapter_iterator_behavior_with_running_service(running_service_with_mock_client: MockServiceContext) -> None:
    """Test adapter iterator behavior with a running service."""
    # Create the service client and adapter
    service_client = ServiceClient(base_url=running_service_with_mock_client.base_url)
    service_client.set_httpx_client(running_service_with_mock_client.httpx_client)
    adapter = ServiceClientAdapter(service_client)

    # Test iterator behavior
    message_iter = adapter.get_messages(max_results=5)
    assert hasattr(message_iter, "__iter__")

    # Convert to list and verify
    messages = list(message_iter)
    assert len(messages) == 1
    assert messages[0].id == running_service_with_mock_client.mock_data["id"]

    # Test iterator exhaustion
    messages_again = list(message_iter)
    assert len(messages_again) == 0  # Iterator should be exhausted

    # Test new iterator
    new_iter = adapter.get_messages(max_results=3)
    new_messages = list(new_iter)
    assert len(new_messages) == 1
    assert new_messages[0].id == running_service_with_mock_client.mock_data["id"]


@pytest.mark.integration
@pytest.mark.local_credentials
def test_adapter_concurrent_operations_with_running_service(running_service_with_mock_client: MockServiceContext) -> None:  # noqa: C901
    """Test adapter with concurrent operations."""
    import queue  # noqa: PLC0415 # literally only used in this test
    import threading  # noqa: PLC0415 # literally only used in this test

    # Create the service client and adapter
    service_client = ServiceClient(base_url=running_service_with_mock_client.base_url)
    service_client.set_httpx_client(running_service_with_mock_client.httpx_client)
    adapter = ServiceClientAdapter(service_client)

    results_queue = queue.Queue()

    def worker_operation(operation_type: str) -> None:
        """Worker function for concurrent operations."""
        try:
            if operation_type == "get_messages":
                messages = list(adapter.get_messages(max_results=1))
                results_queue.put(("success", operation_type, len(messages)))
            elif operation_type == "get_message":
                message = adapter.get_message(running_service_with_mock_client.mock_data["id"])
                results_queue.put(("success", operation_type, message.id))
            elif operation_type == "mark_as_read":
                success = adapter.mark_as_read(running_service_with_mock_client.mock_data["id"])
                results_queue.put(("success", operation_type, success))
            elif operation_type == "delete_message":
                success = adapter.delete_message(running_service_with_mock_client.mock_data["id"])
                results_queue.put(("success", operation_type, success))
        except Exception as e:  # noqa: BLE001
            results_queue.put(("error", operation_type, str(e)))

    # Start multiple threads with different operations
    threads = []
    operations = ["get_messages", "get_message", "mark_as_read", "delete_message"]

    for operation in operations:
        thread = threading.Thread(target=worker_operation, args=(operation,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join(timeout=10)

    # Collect results
    success_count = 0
    error_count = 0

    while not results_queue.empty():
        result_type, operation, data = results_queue.get()
        if result_type == "success":
            success_count += 1
            assert data is not None, f"Operation {operation} returned None"
        else:
            error_count += 1

    # Should have at least some successful operations
    assert success_count > 0, f"No successful operations. Errors: {error_count}"


@pytest.mark.integration
@pytest.mark.local_credentials
def test_adapter_edge_cases_with_running_service(running_service_with_mock_client: MockServiceContext) -> None:
    """Test adapter edge cases with a running service."""
    # Create the service client and adapter
    service_client = ServiceClient(base_url=running_service_with_mock_client.base_url)
    service_client.set_httpx_client(running_service_with_mock_client.httpx_client)
    adapter = ServiceClientAdapter(service_client)

    # Test 1: Empty max_results - the adapter returns all messages when max_results=0
    messages = list(adapter.get_messages(max_results=0))
    # The adapter returns all messages when max_results=0 (not positive)
    assert len(messages) == 1

    # Test 2: Negative max_results
    messages = list(adapter.get_messages(max_results=-1))
    assert len(messages) == 1  # Should still return messages

    # Test 3: Very large max_results
    messages = list(adapter.get_messages(max_results=1000))
    assert len(messages) == 1  # Our mock only returns 1 message

    # Test 4: None max_results (should use default)
    messages = list(adapter.get_messages())
    assert len(messages) == 1


@pytest.mark.integration
@pytest.mark.local_credentials
def test_adapter_logging_with_running_service(
    running_service_with_mock_client: MockServiceContext, caplog: pytest.LogCaptureFixture
) -> None:
    """Test adapter logging with a running service."""
    import logging  # noqa: PLC0415 # literally only used in this test

    # Set up logging to capture adapter logs
    caplog.set_level(logging.INFO)

    # Create the service client and adapter
    service_client = ServiceClient(base_url=running_service_with_mock_client.base_url)
    service_client.set_httpx_client(running_service_with_mock_client.httpx_client)
    adapter = ServiceClientAdapter(service_client)

    # Perform operations that should generate logs
    adapter.get_messages(max_results=1)
    adapter.get_message(running_service_with_mock_client.mock_data["id"])
    adapter.mark_as_read(running_service_with_mock_client.mock_data["id"])
    adapter.delete_message(running_service_with_mock_client.mock_data["id"])

    # Check that logs were generated
    log_messages = [record.message for record in caplog.records]

    # Should have some log messages from the adapter
    assert len(log_messages) > 0, "No log messages generated"

    # Check for specific log patterns
    log_text = " ".join(log_messages)
    assert "Fetching messages" in log_text or "Attempting to" in log_text


@pytest.mark.integration
@pytest.mark.local_credentials
def test_adapter_service_health_with_running_service(running_service_with_mock_client: MockServiceContext) -> None:
    """Test adapter with service health checks."""
    # Test service health using the httpx_client from the fixture
    try:
        response = running_service_with_mock_client.httpx_client.get("/openapi.json")
        assert response.status_code == 200  # noqa: PLR2004 # expected status code
    except AssertionError as e:
        pytest.fail(f"Service health check failed: {e}")
    except RuntimeError as e:
        pytest.fail(f"Service health check failed: {e}")
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"Service health check failed: {e}")

    # Create the service client and adapter
    service_client = ServiceClient(base_url=running_service_with_mock_client.base_url)
    service_client.set_httpx_client(running_service_with_mock_client.httpx_client)
    adapter = ServiceClientAdapter(service_client)

    # Test that adapter works after health check
    messages = list(adapter.get_messages(max_results=1))
    assert len(messages) == 1
    assert messages[0].id == running_service_with_mock_client.mock_data["id"]


@pytest.mark.integration
@pytest.mark.local_credentials
def test_adapter_data_consistency_with_running_service(running_service_with_mock_client: MockServiceContext) -> None:
    """Test adapter data consistency with a running service."""
    # Create the service client and adapter
    service_client = ServiceClient(base_url=running_service_with_mock_client.base_url)
    service_client.set_httpx_client(running_service_with_mock_client.httpx_client)
    adapter = ServiceClientAdapter(service_client)

    # Test data consistency across multiple calls
    for _ in range(3):
        # Get messages
        messages = list(adapter.get_messages(max_results=1))
        assert len(messages) == 1
        message = messages[0]

        # Verify consistent data
        assert message.id == running_service_with_mock_client.mock_data["id"]
        assert message.subject == running_service_with_mock_client.mock_data["subject"]
        assert message.from_ == running_service_with_mock_client.mock_data["from"]
        assert message.to == running_service_with_mock_client.mock_data["to"]
        assert message.date == running_service_with_mock_client.mock_data["date"]
        assert message.body == running_service_with_mock_client.mock_data["body"]

        # Get specific message
        specific_message = adapter.get_message(running_service_with_mock_client.mock_data["id"])
        assert specific_message.id == message.id
        assert specific_message.subject == message.subject
        assert specific_message.from_ == message.from_
        assert specific_message.to == message.to
        assert specific_message.date == message.date
        assert specific_message.body == message.body


@pytest.mark.integration
@pytest.mark.local_credentials
def test_verify_mock_gmail_client_isolation(running_service_with_mock_client: MockServiceContext) -> None:
    """Verify that we are NEVER using the real Gmail client."""
    # Create the service client and adapter
    service_client = ServiceClient(base_url=running_service_with_mock_client.base_url)
    service_client.set_httpx_client(running_service_with_mock_client.httpx_client)
    adapter = ServiceClientAdapter(service_client)

    # Test that we get our mock data, not real Gmail data
    messages = list(adapter.get_messages(max_results=1))
    assert len(messages) == 1

    message = messages[0]

    # Verify we're getting our mock data, not real Gmail data
    assert message.id == "test_msg_123"  # Our mock ID
    assert message.subject == "Test Integration Message"  # Our mock subject
    assert message.from_ == "sender@test.com"  # Our mock sender
    assert message.to == "recipient@test.com"  # Our mock recipient
    assert message.date == "2025-01-15T10:30:00Z"  # Our mock date
    assert message.body == "This is a test message for integration testing."  # Our mock body

    # Test that invalid IDs raise RuntimeError (not real Gmail errors)
    with pytest.raises(RuntimeError, match="Message with ID invalid-message-id not found"):
        adapter.get_message("invalid-message-id")

    # Test that operations with invalid IDs return True (service always returns success)
    # Note: The FastAPI service doesn't propagate boolean return values from Gmail client
    # It just returns success messages regardless of the underlying client result
    mark_result = adapter.mark_as_read("invalid-message-id")
    assert mark_result is True  # Service always returns success

    delete_result = adapter.delete_message("invalid-message-id")
    assert delete_result is True  # Service always returns success

    # Verify mock Gmail client was called with correct parameters
    running_service_with_mock_client.mock_client.get_messages.assert_called_once()
    running_service_with_mock_client.mock_client.get_message.assert_called_once_with("invalid-message-id")
    running_service_with_mock_client.mock_client.mark_as_read.assert_called_once_with("invalid-message-id")
    running_service_with_mock_client.mock_client.delete_message.assert_called_once_with("invalid-message-id")
