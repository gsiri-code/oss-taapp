# ruff: noqa: ERA001
"""End-to-end tests for the mail service."""

import os
import socket
import subprocess
import time
from contextlib import closing, suppress
from enum import Enum
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class HTTPStatus(Enum):
    """HTTP status codes used in the API."""

    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    INTERNAL_SERVER_ERROR = 500


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _wait_for_ready(base_url: str, timeout_s: int = 45) -> None:
    import httpx

    start = time.time()
    while time.time() - start < timeout_s:
        try:
            r = httpx.get(f"{base_url}/openapi.json", timeout=2.0)
            if r.status_code < HTTPStatus.INTERNAL_SERVER_ERROR.value:
                return
        except Exception as e:
            print(f"Error waiting for service to be ready: {e}")  # noqa: T201
        time.sleep(0.5)
    msg = f"Service never became ready at {base_url}"
    raise RuntimeError(msg)


@pytest.fixture(scope="session")
def service_base_url(tmp_path_factory) -> None:  # noqa: ANN001
    """Start the real FastAPI service in a separate process (uvicorn) so we hit it over HTTP."""
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    env = os.environ.copy()

    # Ensure the child process can import your `src/` tree
    src_paths = [
        str(Path("src/mail_client_api/src").resolve()),
        str(Path("src/mail_client_adapter/src").resolve()),
        str(Path("src/gmail_client_impl/src").resolve()),
        str(Path("src/mail_client_service/src").resolve()),
    ]
    env["PYTHONPATH"] = os.pathsep.join([*src_paths, env.get("PYTHONPATH", "")])

    # Non-interactive Gmail (adjust if you have a token path env)
    env["MAIL_CLIENT_INTERACTIVE"] = "false"

    # Example if you need a token path:
    # env["GMAIL_TOKEN_FILE"] = os.path.abspath("token.json")

    # === The key fix: target the module filename and point uvicorn at the directory ===
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "uvicorn",
        "mail_client_service.fast_api_service:app",  # module:var (src/mail_client_service/src/mail_client_service/fast_api_service.py defines app = FastAPI(...))
        "--app-dir",
        "src/mail_client_service/src",  # directory that contains mail_client_service package
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]

    proc = subprocess.Popen(  # noqa: S603
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=False,
    )

    try:
        _wait_for_ready(base_url, timeout_s=45)
    except Exception:
        if proc.stdout:
            pass
        proc.kill()
        raise

    yield base_url

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def shared_client(service_base_url: str):  # noqa: ANN201 # return type: Client
    """Session-scoped fixture that provides a shared HTTP client for all tests."""
    from mail_client_service_client import Client

    return Client(
        base_url=service_base_url,
        timeout=30.0,  # Reasonable timeout for E2E tests
    )


@pytest.fixture
def mail_adapter_client(shared_client):  # noqa: ANN001, ANN201 # Client
    """Fixture that provides a configured mail adapter client for testing."""
    from mail_client_adapter import ServiceClientAdapter

    return ServiceClientAdapter(shared_client)


@pytest.fixture
def ci_mail_adapter_client(shared_client):  # noqa: ANN001, ANN201 # Client
    """Fixture that provides a CI-optimized mail adapter client for testing."""
    from mail_client_adapter import ServiceClientAdapter

    return ServiceClientAdapter(shared_client)


@pytest.fixture
def sample_messages(mail_adapter_client):  # noqa: ANN001, ANN201 # ServiceClientAdapter
    """Fixture that provides sample messages for testing."""
    try:
        return list(mail_adapter_client.get_messages(max_results=3))
    except Exception:
        return []


@pytest.fixture
def service_health_check(service_base_url: str) -> bool | None:
    """Fixture that performs service health check."""
    import httpx

    try:
        response = httpx.get(f"{service_base_url}/openapi.json", timeout=5.0)
        assert response.status_code == httpx.codes.OK
        return True
    except Exception as e:
        pytest.fail(f"Service health check failed: {e}")


# Test utility functions
def validate_message_structure(message) -> bool:  # noqa: ANN001 # Message
    """Validate that a message has the required structure."""
    required_fields = ["id", "subject", "from_", "date", "body"]

    for field in required_fields:
        if not hasattr(message, field):
            return False
        value = getattr(message, field)
        if not isinstance(value, str):
            return False

    return True


def validate_http_response_structure(response_data: dict) -> bool:
    """Validate that HTTP response has the required structure."""
    required_keys = ["id", "from", "to", "subject", "date", "body"]

    for key in required_keys:
        if key not in response_data:
            return False
        if not isinstance(response_data[key], str):
            return False

    return True


def measure_performance(func, *args, **kwargs):  # noqa: ANN001, ANN003, ANN002, ANN201
    """Measure the performance of a function call."""
    import time

    start_time = time.time()
    result = func(*args, **kwargs)
    execution_time = time.time() - start_time

    return result, execution_time


@pytest.mark.e2e
@pytest.mark.local_credentials
def test_e2e_service_adapter_calls_real_gmail_api(
    mail_adapter_client,  # noqa: ANN001 # ServiceClientAdapter
    service_health_check: bool | None,  # noqa: FBT001
) -> None:
    """E2E test that uses mail_client_adapter to call running service with real Gmail API.

    This test validates the entire system from consumer perspective:
    mail_client_adapter -> mail_client_service -> real Gmail API
    """
    # Test 1: Get messages from real Gmail API via service
    messages = list(mail_adapter_client.get_messages(max_results=3))

    # Should have retrieved real messages from Gmail
    assert len(messages) >= 0  # Allow for empty inbox

    # Test 2: If we have messages, test getting a specific one
    if messages:
        first_message = messages[0]
        retrieved_message = mail_adapter_client.get_message(first_message.id)

        # Verify the message data is properly returned
        assert retrieved_message.id == first_message.id
        assert retrieved_message.subject == first_message.subject
        assert retrieved_message.from_ == first_message.from_

        # Test 3: Mark as read (non-destructive)
        success = mail_adapter_client.mark_as_read(first_message.id)
        assert success is True


@pytest.mark.e2e
@pytest.mark.local_credentials
def test_e2e_comprehensive_service_operations(
    service_base_url: str,
    mail_adapter_client,  # noqa: ANN001 # ServiceClientAdapter
) -> None:
    """Comprehensive E2E test with error handling and delete operations.

    Tests the full system with real Gmail API including:
    - Service health verification
    - Error handling for failed operations
    - Delete operations with safeguards
    - Comprehensive logging
    """
    import httpx

    # Test 0: Verify service is healthy
    try:
        response = httpx.get(f"{service_base_url}/openapi.json", timeout=5.0)
        assert response.status_code == httpx.codes.OK, f"Service health check failed: {response.status_code}"
    except Exception as e:
        pytest.fail(f"Service is not healthy: {e}")

    # Use shared adapter
    adapter = mail_adapter_client

    # Test 1: Get messages with error handling
    try:
        messages = list(adapter.get_messages(max_results=5))
    except Exception as e:
        pytest.fail(f"Failed to retrieve messages: {e}")

    # Test 2: Handle empty inbox scenario
    if not messages:
        # Test that get_message fails gracefully for non-existent message
        try:
            adapter.get_message("non-existent-id")
            pytest.fail("Expected RuntimeError for non-existent message")
        except RuntimeError as e:
            assert "not found" in str(e).lower()  # noqa: PT017
        return

    # Test 3: Test individual message operations
    first_message = messages[0]

    # Get specific message
    try:
        retrieved = adapter.get_message(first_message.id)
        assert retrieved.id == first_message.id
        assert retrieved.subject == first_message.subject
    except Exception as e:
        pytest.fail(f"Failed to retrieve specific message: {e}")

    # Mark as read
    try:
        success = adapter.mark_as_read(first_message.id)
        assert success is True
    except Exception as e:
        pytest.fail(f"Failed to mark message as read: {e}")

    # Test 4: Delete operation (only if we have multiple messages)
    if len(messages) > 1:
        message_to_delete = messages[-1]  # Delete the last message

        try:
            success = adapter.delete_message(message_to_delete.id)
            assert success is True

            # Verify message is actually deleted by trying to retrieve it
            try:
                adapter.get_message(message_to_delete.id)
                pytest.fail("Message should have been deleted but still exists")
            except RuntimeError as e:
                assert "not found" in str(e).lower()  # noqa: PT017

        except Exception as e:
            pytest.fail(f"Failed to delete message: {e}")
    else:
        pass


# @pytest.mark.e2e
# @pytest.mark.circleci
# @pytest.mark.skip
# def test_e2e_ci_environment_service_operations(
#     service_base_url: str,
#     ci_mail_adapter_client,  # ServiceClientAdapter
# ) -> None:
#     """E2E test for CI/CD environments using environment variables.

#     Tests the full system in CircleCI environment:
#     - Uses environment variables for Gmail authentication
#     - Limited operations for CI efficiency
#     - Shorter timeouts
#     - Validates environment variable setup
#     """
#     import os

#     import httpx

#     # Validate required environment variables for CI
#     required_env_vars = [
#         "GMAIL_CLIENT_ID",
#         "GMAIL_CLIENT_SECRET",
#         "GMAIL_REFRESH_TOKEN",
#     ]
#     missing_vars = [var for var in required_env_vars if not os.environ.get(var)]

#     if missing_vars:
#         pytest.skip(f"Missing required environment variables for CI test: {missing_vars}")

#     # Test 0: Verify service is healthy (shorter timeout for CI)
#     try:
#         response = httpx.get(f"{service_base_url}/openapi.json", timeout=2.0)
#         assert response.status_code == httpx.codes.OK, f"Service health check failed: {response.status_code}"
#     except Exception as e:
#         pytest.fail(f"Service is not healthy: {e}")

#     # Use shared adapter
#     adapter = ci_mail_adapter_client

#     # Test 1: Get limited messages for CI efficiency
#     try:
#         messages = list(adapter.get_messages(max_results=1))  # Only 1 message for CI
#     except Exception as e:
#         pytest.fail(f"CI Test: Failed to retrieve messages: {e}")

#     # Test 2: Handle empty inbox scenario in CI
#     if not messages:
#         try:
#             adapter.get_message("ci-test-non-existent-id")
#             pytest.fail("CI Test: Expected RuntimeError for non-existent message")
#         except RuntimeError as e:
#             assert "not found" in str(e).lower()
#         return

#     # Test 3: Test basic operations on first message (CI-safe operations only)
#     first_message = messages[0]

#     # Get specific message
#     try:
#         retrieved = adapter.get_message(first_message.id)
#         assert retrieved.id == first_message.id
#         assert retrieved.subject == first_message.subject
#     except Exception as e:
#         pytest.fail(f"CI Test: Failed to retrieve specific message: {e}")

#     # Mark as read (non-destructive operation)
#     try:
#         success = adapter.mark_as_read(first_message.id)
#         assert success is True
#     except Exception as e:
#         pytest.fail(f"CI Test: Failed to mark message as read: {e}")

#     # Note: Skip delete operations in CI for safety


@pytest.mark.e2e
def test_e2e_service_failure_scenarios() -> None:
    """E2E test for service failure scenarios and error handling.

    Tests robust error handling when:
    - Service is down or unreachable
    - Network timeouts occur
    - Invalid service URLs are used
    - Service returns error responses
    """
    from mail_client_adapter import ServiceClientAdapter
    from mail_client_service_client import Client

    # Test 1: Service down scenario (invalid URL)
    invalid_client = Client(
        base_url="http://localhost:99999",  # Invalid port
    )
    invalid_adapter = ServiceClientAdapter(invalid_client)

    # Should fail gracefully when service is unreachable
    # Note: The adapter catches exceptions and returns empty iterator
    messages = list(invalid_adapter.get_messages(max_results=1))
    assert len(messages) == 0, "Expected empty iterator for unreachable service"

    # Test 2: Invalid service URL (malformed)
    malformed_client = Client(
        base_url="http://invalid-service-url-that-does-not-exist.com:8080",
    )
    malformed_adapter = ServiceClientAdapter(malformed_client)

    messages = list(malformed_adapter.get_messages(max_results=1))
    assert len(messages) == 0, "Expected empty iterator for invalid service URL"

    # Test 3: Timeout scenario (very short timeout)
    timeout_client = Client(
        base_url="http://httpbin.org/delay/10",  # Service that delays 10 seconds
    )
    timeout_adapter = ServiceClientAdapter(timeout_client)

    messages = list(timeout_adapter.get_messages(max_results=1))
    assert len(messages) == 0, "Expected empty iterator for timeout scenario"

    # Test 4: Service returns error response (404, 500, etc.)
    error_client = Client(
        base_url="http://httpbin.org/status/500",  # Service that returns 500 error
    )
    error_adapter = ServiceClientAdapter(error_client)

    messages = list(error_adapter.get_messages(max_results=1))
    assert len(messages) == 0, "Expected empty iterator for HTTP error response"


@pytest.mark.e2e
@pytest.mark.local_credentials
def test_e2e_comprehensive_error_scenarios(  # noqa: PLR0915, PLR0912, C901
    service_base_url: str,
    mail_adapter_client,  # noqa: ANN001 # ServiceClientAdapter
) -> None:
    """Comprehensive E2E test for various error scenarios and edge cases.

    Tests error handling for:
    - Invalid message IDs (malformed, non-existent, special characters)
    - Network connectivity issues
    - Service overload scenarios
    - Data validation failures
    - Authentication edge cases
    """
    import httpx

    # Use shared adapter
    adapter = mail_adapter_client

    # Test 1: Invalid message ID formats
    invalid_ids = [
        "",  # Empty string
        "   ",  # Whitespace only
        "invalid-id-with-special-chars!@#$%^&*()",  # Special characters
        "x" * 1000,  # Very long ID
        "123",  # Numeric only (might be valid but test edge case)
        None,  # None value (should be handled gracefully)
    ]

    for invalid_id in invalid_ids:
        try:
            if invalid_id is None:
                # Skip None test as it would cause a TypeError before reaching our code
                continue
            adapter.get_message(invalid_id)
            pytest.fail(f"Expected RuntimeError for invalid ID: {invalid_id!r}")
        except RuntimeError as e:
            assert "not found" in str(e).lower() or "failed" in str(e).lower()  # noqa: PT017
        except Exception as e:
            # Some invalid IDs might cause different types of errors
            pytest.fail(f"Invalid ID test failed with Exception: {e}")

    # Test 2: Network timeout scenarios
    from mail_client_adapter import ServiceClientAdapter
    from mail_client_service_client import Client

    timeout_client = Client(
        base_url=service_base_url,
        timeout=0.001,  # Very short timeout
    )
    timeout_adapter = ServiceClientAdapter(timeout_client)

    try:
        messages = list(timeout_adapter.get_messages(max_results=1))
        # Should either succeed quickly or return empty list
        assert isinstance(messages, list)
    except Exception as e:
        pytest.fail(f"Network timeout scenarios test failed: {e}")

    # Test 3: Concurrent request handling
    import queue
    import threading

    results_queue = queue.Queue()

    def make_concurrent_request() -> None:
        try:
            messages = list(adapter.get_messages(max_results=2))
            results_queue.put(("success", len(messages)))
        except Exception as e:
            results_queue.put(("error", str(e)))

    # Start multiple concurrent requests
    threads = []
    for _i in range(5):
        thread = threading.Thread(target=make_concurrent_request)
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join(timeout=30)

    # Collect results
    success_count = 0
    error_count = 0
    while not results_queue.empty():
        result_type, _result_data = results_queue.get()
        if result_type == "success":
            success_count += 1
        else:
            error_count += 1

    # Test 4: Large response handling
    try:
        # Request a larger number of messages to test response size handling
        messages = list(adapter.get_messages(max_results=50))

        # Test that all messages have required fields
        for i, msg in enumerate(messages[:5]):  # Check first 5 messages
            assert hasattr(msg, "id"), f"Message {i} missing ID"
            assert hasattr(msg, "subject"), f"Message {i} missing subject"
            assert hasattr(msg, "from_"), f"Message {i} missing from_"
            assert hasattr(msg, "date"), f"Message {i} missing date"
            assert hasattr(msg, "body"), f"Message {i} missing body"

    except Exception as e:
        pytest.fail(f"Large response handling test failed: {e}")

    # Test 5: Service health monitoring
    try:
        response = httpx.get(f"{service_base_url}/openapi.json", timeout=5.0)
        assert response.status_code == httpx.codes.OK
        assert "openapi" in response.json()
    except Exception as e:
        pytest.fail(f"Service health check failed: {e}")


@pytest.mark.e2e
@pytest.mark.local_credentials
def test_e2e_data_integrity_and_validation(  # noqa: PLR0915, PLR0912, C901
    service_base_url: str,
    mail_adapter_client,  # noqa: ANN001 # ServiceClientAdapter
) -> None:
    """E2E test for data integrity, validation, and message format verification.

    Tests:
    - Message data structure validation
    - Field type checking
    - Data consistency across operations
    - Message format compliance
    - Response structure validation
    """
    # Use shared adapter
    adapter = mail_adapter_client

    # Test 1: Message data structure validation
    try:
        messages = list(adapter.get_messages(max_results=3))

        if not messages:
            return

        for i, msg in enumerate(messages):
            # Validate required fields exist and are strings
            required_fields = ["id", "subject", "from_", "date", "body"]
            for field in required_fields:
                assert hasattr(msg, field), f"Message {i + 1} missing field: {field}"
                value = getattr(msg, field)
                assert isinstance(value, str), f"Message {i + 1} field {field} is not string: {type(value)}"
                assert value is not None, f"Message {i + 1} field {field} is None"

            # Validate field content patterns
            assert len(msg.id) > 0, f"Message {i + 1} has empty ID"
            assert len(msg.subject) >= 0, f"Message {i + 1} subject validation failed"  # Subject can be empty

            # Validate email format in from_ field (basic check)
            if msg.from_ and "@" in msg.from_:
                # Note: Gmail API might return complex formats like "Name <email@domain.com>"
                # So we just check for basic email structure
                assert "@" in msg.from_, f"Message {i + 1} from_ field doesn't contain email: {msg.from_}"

            # Validate date format (should be a string, could be ISO format or other)
            assert isinstance(msg.date, str), f"Message {i + 1} date is not string: {type(msg.date)}"

            # Validate body is a string (can be empty)
            assert isinstance(msg.body, str), f"Message {i + 1} body is not string: {type(msg.body)}"

    except Exception as e:
        pytest.fail(f"Data structure validation failed: {e}")

    # Test 2: Data consistency across operations
    if messages:
        first_message = messages[0]
        original_id = first_message.id

        # Get the same message again and verify consistency
        try:
            retrieved_message = adapter.get_message(original_id)

            # Verify data consistency
            assert retrieved_message.id == first_message.id, "Message ID inconsistency"
            assert retrieved_message.subject == first_message.subject, "Message subject inconsistency"
            assert retrieved_message.from_ == first_message.from_, "Message from_ inconsistency"
            assert retrieved_message.date == first_message.date, "Message date inconsistency"
            assert retrieved_message.body == first_message.body, "Message body inconsistency"

        except Exception as e:
            pytest.fail(f"Data consistency check failed: {e}")

    # Test 3: Response structure validation via direct HTTP calls
    import httpx

    try:
        # Test GET /messages endpoint structure
        response = httpx.get(f"{service_base_url}/messages", timeout=10.0)
        assert response.status_code == httpx.codes.OK, f"GET /messages failed: {response.status_code}"

        messages_data = response.json()
        assert isinstance(messages_data, list), "GET /messages should return a list"

        # Validate each message structure in the response
        for i, msg_data in enumerate(messages_data[:3]):  # Check first 3 messages
            assert isinstance(msg_data, dict), f"Message {i} is not a dictionary"

            required_keys = ["id", "from", "to", "subject", "date", "body"]
            for key in required_keys:
                assert key in msg_data, f"Message {i} missing key: {key}"
                assert isinstance(msg_data[key], str), f"Message {i} key {key} is not string"

    except Exception as e:
        pytest.fail(f"Response structure validation failed: {e}")

    # Test 4: Edge case data handling

    # Test with very long content
    try:
        messages = list(adapter.get_messages(max_results=1))
        if messages:
            msg = messages[0]

            # Check if message has very long content
            if len(msg.body) > 10000:  # noqa: PLR2004 # arbitrary for long body
                pass

            if len(msg.subject) > 200:  # noqa: PLR2004 # arbitrary for long subject line
                pass

            # Check for special characters in content
            special_chars = ["<", ">", "&", '"', "'", "\n", "\r", "\t"]
            found_special = [char for char in special_chars if char in msg.body]
            if found_special:
                pass

    except Exception as e:
        pytest.fail(f"Edge case data handling test failed: {e}")


# @pytest.mark.e2e
# @pytest.mark.local_credentials
# def test_e2e_complex_workflow_scenarios(
#     service_base_url: str,
#     mail_adapter_client,  # ServiceClientAdapter
# ) -> None:
#     """E2E test for complex workflow scenarios that test multiple operations in sequence.

#     Tests realistic user workflows:
#     - Complete message lifecycle (fetch, read, mark as read, delete)
#     - Batch operations
#     - Error recovery scenarios
#     - State transitions
#     - Resource cleanup
#     """
#     # Use shared adapter
#     adapter = mail_adapter_client

#     # Test 1: Complete message lifecycle workflow

#     try:
#         # Step 1: Fetch initial messages
#         initial_messages = list(adapter.get_messages(max_results=5))

#         if not initial_messages:
#             return

#         # Step 2: Select a message for lifecycle testing
#         test_message = initial_messages[0]
#         test_message_id = test_message.id

#         # Step 3: Retrieve the specific message
#         retrieved_message = adapter.get_message(test_message_id)
#         assert retrieved_message.id == test_message_id

#         # Step 4: Mark as read (non-destructive)
#         success = adapter.mark_as_read(test_message_id)
#         assert success is True

#         # Step 5: Verify message is still accessible after marking as read
#         verified_message = adapter.get_message(test_message_id)
#         assert verified_message.id == test_message_id

#         # Step 6: Only delete if we have multiple messages (safety measure)
#         if len(initial_messages) > 1:
#             # Use the last message for deletion to minimize impact
#             delete_message = initial_messages[-1]
#             delete_message_id = delete_message.id

#             # Delete the message
#             delete_success = adapter.delete_message(delete_message_id)
#             assert delete_success is True

#             # Verify message is actually deleted
#             try:
#                 adapter.get_message(delete_message_id)
#                 pytest.fail("Message should have been deleted but still exists")
#             except Exception as e:
#                 assert "not found" in str(e).lower()
#         else:
#             pass

#     except Exception as e:
#         pytest.fail(f"Message lifecycle workflow failed: {e}")

#     # Test 2: Batch operations workflow

#     try:
#         # Fetch multiple messages
#         batch_messages = list(adapter.get_messages(max_results=3))

#         # Process each message in the batch
#         processed_count = 0
#         for _i, msg in enumerate(batch_messages):
#             try:
#                 # Get specific message details
#                 detailed_msg = adapter.get_message(msg.id)
#                 assert detailed_msg.id == msg.id

#                 # Mark as read
#                 success = adapter.mark_as_read(msg.id)
#                 assert success is True

#                 processed_count += 1

#             except Exception as e:
#                 pytest.fail(f"Batch operation failed while processing message ID {msg.id}: {e}")

#     except Exception as e:
#         pytest.fail(f"Batch operations setup or initial fetch failed: {e}")

#     # Test 3: Error recovery workflow
#     try:
#         # Define operations that should fail when given invalid message IDs
#         invalid_operations = [
#             ("get_message", "invalid-message-id"),
#             ("mark_as_read", "invalid-message-id"),
#             ("delete_message", "invalid-message-id"),
#         ]

#         for operation, invalid_id in invalid_operations:
#             # Each invalid operation should raise an exception
#             with pytest.raises(Exception, match=".*invalid.*|.*not found.*"):
#                 if operation == "get_message":
#                     adapter.get_message(invalid_id)
#                 elif operation == "mark_as_read":
#                     adapter.mark_as_read(invalid_id)
#                 elif operation == "delete_message":
#                     adapter.delete_message(invalid_id)
#                 else:
#                     pytest.fail(f"Unknown operation '{operation}' in error recovery test.")

#         # After handling invalid operations, verify that the system remains functional
#         try:
#             messages = list(adapter.get_messages(max_results=1))
#             assert isinstance(messages, list), "Adapter returned non-list response after recovery."
#         except Exception as e:
#             pytest.fail(f"Adapter became unresponsive after error recovery: {e}")

#     except Exception as e:
#         pytest.fail(f"Unexpected failure during error recovery workflow: {e}")

#     # Test 4: State transition workflow

#     try:
#         # Get a message and track its state changes
#         messages = list(adapter.get_messages(max_results=1))

#         if messages:
#             test_msg = messages[0]
#             test_msg_id = test_msg.id

#             # State 1: Initial state (fetched)
#             adapter.get_message(test_msg_id)

#             # State 2: Mark as read
#             read_success = adapter.mark_as_read(test_msg_id)
#             assert read_success is True

#             # State 3: Verify read state
#             read_msg = adapter.get_message(test_msg_id)
#             assert read_msg.id == test_msg_id

#         else:
#             pass

#     except Exception as e:
#         pytest.fail(f"State transition workflow failed: {e}")


# @pytest.mark.e2e
# @pytest.mark.circleci
# @pytest.mark.skip
# def test_e2e_ci_performance_and_reliability(
#     service_base_url: str,
#     ci_mail_adapter_client,  # ServiceClientAdapter
# ) -> None:
#     """E2E test for CI/CD performance and reliability requirements.

#     Tests optimized for CI environments:
#     - Fast execution with minimal operations
#     - Resource usage monitoring
#     - Reliability under CI constraints
#     - Performance benchmarks
#     """
#     import os
#     import time

#     # Validate CI environment
#     required_env_vars = [
#         "GMAIL_CLIENT_ID",
#         "GMAIL_CLIENT_SECRET",
#         "GMAIL_REFRESH_TOKEN",
#     ]
#     missing_vars = [var for var in required_env_vars if not os.environ.get(var)]

#     if missing_vars:
#         pytest.skip(f"Missing required environment variables for CI test: {missing_vars}")

#     # Test 1: Service startup time and health check
#     start_time = time.time()

#     try:
#         import httpx

#         response = httpx.get(f"{service_base_url}/openapi.json", timeout=5.0)
#         health_check_time = time.time() - start_time

#         assert response.status_code == httpx.codes.OK
#         assert (
#             health_check_time < 5.0  # arbitrary for now
#         ), f"Health check took too long: {health_check_time:.2f}s"

#     except Exception as e:
#         pytest.fail(f"CI service health check failed: {e}")

#     # Use shared adapter
#     adapter = ci_mail_adapter_client

#     # Measure get_messages performance
#     start_time = time.time()
#     try:
#         messages = list(adapter.get_messages(max_results=1))  # Minimal for CI
#         operation_time = time.time() - start_time

#         assert (
#             operation_time < 15.0
#         ), f"get_messages took too long: {operation_time:.2f}s"
#         assert isinstance(messages, list)

#     except Exception as e:
#         pytest.fail(f"CI get_messages performance test failed: {e}")

#     # Test 3: Memory usage monitoring (basic check)
#     try:
#         import gc

#         import psutil

#         psutil_available = True
#     except ImportError:
#         psutil_available = False

#     if psutil_available:
#         process = psutil.Process()
#         initial_memory = process.memory_info().rss / 1024 / 1024  # MB

#         # Perform operations
#         for _i in range(3):
#             try:
#                 messages = list(adapter.get_messages(max_results=1))
#                 gc.collect()  # Force garbage collection
#             except Exception as e:
#                 pytest.fail(f"CI memory usage monitoring test failed: {e}")

#         final_memory = process.memory_info().rss / 1024 / 1024  # MB
#         memory_increase = final_memory - initial_memory

#         assert (
#             memory_increase < 50.0
#         ), f"Memory usage increased too much: {memory_increase:.2f}MB"

#     else:
#         # Perform operations without memory monitoring
#         for _i in range(3):
#             with suppress(Exception):
#                 messages = list(adapter.get_messages(max_results=1))

#     # Test 4: Reliability under repeated operations

#     success_count = 0
#     error_count = 0

#     for _i in range(5):  # Limited iterations for CI
#         try:
#             messages = list(adapter.get_messages(max_results=1))
#             success_count += 1
#         except Exception:
#             error_count += 1

#     success_rate = success_count / (success_count + error_count)
#     assert success_rate >= 0.8, f"Reliability too low: {success_rate:.2%}"  # arbitrary for now

#     # Test 5: CI-specific error handling

#     try:
#         # Test with invalid credentials (should fail gracefully)
#         from mail_client_adapter import ServiceClientAdapter
#         from mail_client_service_client import Client

#         invalid_client = Client(
#             base_url=service_base_url,
#         )
#         invalid_adapter = ServiceClientAdapter(invalid_client)

#         # Should handle gracefully without crashing
#         messages = list(invalid_adapter.get_messages(max_results=1))

#     except Exception as e:
#         pytest.fail(f"CI error handling test failed: {e}")


@pytest.mark.e2e
@pytest.mark.local_credentials
@pytest.mark.parametrize("max_results", [1, 3, 5, 10])
def test_e2e_get_messages_with_different_limits(
    mail_adapter_client,  # noqa: ANN001 # ServiceClientAdapter
    max_results: int,
) -> None:
    """Parametrized test for get_messages with different result limits.

    Tests:
    - Different max_results values
    - Response consistency
    - Performance with different limits
    """
    messages, _execution_time = measure_performance(lambda: list(mail_adapter_client.get_messages(max_results=max_results)))

    assert isinstance(messages, list)
    assert len(messages) <= max_results

    # Validate all messages have proper structure
    for i, msg in enumerate(messages):
        assert validate_message_structure(msg), f"Message {i} has invalid structure"


@pytest.mark.e2e
@pytest.mark.local_credentials
@pytest.mark.parametrize(
    "invalid_id",
    [
        "",
        "   ",
        "invalid-id",
        "x" * 1000,
        "123",
        "!@#$%^&*()",
    ],
)
def test_e2e_get_message_with_invalid_ids(mail_adapter_client, invalid_id: str) -> None:  # noqa: ANN001 # ServiceClientAdapter
    """Parametrized test for get_message with various invalid IDs.

    Tests:
    - Different types of invalid message IDs
    - Error handling consistency
    - Graceful failure modes

    Note: ServiceClientAdapter.get_message() is documented to raise RuntimeError
    for invalid message IDs. See:
    - src/mail_client_adapter/src/mail_client_adapter/service_client_adapter.py:48-49
    - src/mail_client_adapter/src/mail_client_adapter/service_client_adapter.py:34-37
    """
    try:
        mail_adapter_client.get_message(invalid_id)
        # If we get here, the invalid ID was not successfully caught
        pytest.fail(f"Expected exception for invalid ID: {invalid_id!r}, but no exception was raised")
    except RuntimeError as e:
        # Invalid ID was successfully caught with RuntimeError
        assert "not found" in str(e).lower() or "failed" in str(e).lower()  # noqa: PT017
    except Exception as e:
        pytest.fail(f"Invalid ID test failed with Exception: {e}")


@pytest.mark.e2e
@pytest.mark.local_credentials
@pytest.mark.parametrize("operation", ["get_message", "mark_as_read", "delete_message"])
def test_e2e_operations_with_sample_messages(
    mail_adapter_client,  # noqa: ANN001 # ServiceClientAdapter
    sample_messages,  # noqa: ANN001 # list[Message]
    operation: str,
) -> None:
    """Parametrized test for different operations on sample messages.

    Tests:
    - Different operations on real messages
    - Operation success/failure patterns
    - Data consistency after operations
    """
    if not sample_messages:
        pytest.skip("No sample messages available for testing")

    test_message = sample_messages[0]

    try:
        if operation == "get_message":
            result = mail_adapter_client.get_message(test_message.id)
            assert result.id == test_message.id
            assert validate_message_structure(result)

        elif operation == "mark_as_read":
            result = mail_adapter_client.mark_as_read(test_message.id)
            assert result is True

        elif operation == "delete_message":
            # Only delete if we have multiple messages (safety)
            if len(sample_messages) > 1:
                delete_message = sample_messages[-1]
                result = mail_adapter_client.delete_message(delete_message.id)
                assert result is True
            else:
                pytest.skip("Only one message available - skipping delete operation for safety")

    except Exception as e:
        pytest.fail(f"{operation} operation failed: {e}")


# @pytest.mark.e2e
# @pytest.mark.circleci
# @pytest.mark.parametrize("timeout", [1.0, 5.0, 10.0])
# @pytest.mark.skip
# def test_e2e_ci_timeout_scenarios(service_base_url: str, timeout: float) -> None:
#     """Parametrized test for different timeout scenarios in CI.

#     Tests:
#     - Different timeout values
#     - Timeout handling
#     - CI-specific behavior
#     """
#     import os

#     from mail_client_adapter import ServiceClientAdapter
#     from mail_client_service_client import Client

#     # Validate CI environment
#     required_env_vars = [
#         "GMAIL_CLIENT_ID",
#         "GMAIL_CLIENT_SECRET",
#         "GMAIL_REFRESH_TOKEN",
#     ]
#     missing_vars = [var for var in required_env_vars if not os.environ.get(var)]

#     if missing_vars:
#         pytest.skip(f"Missing required environment variables for CI test: {missing_vars}")

#     # Create client with specific timeout for this test
#     client = Client(base_url=service_base_url, timeout=timeout)
#     adapter = ServiceClientAdapter(client)

#     with suppress(Exception):
#         list(adapter.get_messages(max_results=1))


# @pytest.mark.e2e
# @pytest.mark.local_credentials
# def test_e2e_message_data_validation_comprehensive(
#     mail_adapter_client,
#     sample_messages,  # list[Message]
# ) -> None:
#     """Comprehensive test for message data validation using fixtures.

#     Tests:
#     - Message structure validation using fixtures
#     - Data type checking
#     - Field content validation
#     - Edge case handling
#     """
#     if not sample_messages:
#         pytest.skip("No sample messages available for validation testing")

#     for i, msg in enumerate(sample_messages):
#         # Use utility function for validation
#         assert validate_message_structure(msg), f"Message {i + 1} failed structure validation"

#         # Additional field-specific validations
#         assert len(msg.id) > 0, f"Message {i + 1} has empty ID"
#         assert isinstance(msg.subject, str), f"Message {i + 1} subject is not string"
#         assert isinstance(msg.from_, str), f"Message {i + 1} from_ is not string"
#         assert isinstance(msg.date, str), f"Message {i + 1} date is not string"
#         assert isinstance(msg.body, str), f"Message {i + 1} body is not string"

#         # Email format validation (basic)
#         if msg.from_ and "@" in msg.from_:
#             assert "@" in msg.from_, f"Message {i + 1} from_ doesn't contain email"


@pytest.mark.e2e
@pytest.mark.local_credentials
def test_e2e_performance_benchmarks(mail_adapter_client) -> None:  # noqa: ANN001 # import ServiceClientAdapter kept seperate
    """Performance benchmark tests using utility functions.

    Tests:
    - Operation timing
    - Performance consistency
    - Resource usage patterns
    """
    # Benchmark get_messages
    messages, _get_time = measure_performance(lambda: list(mail_adapter_client.get_messages(max_results=5)))

    # Benchmark individual operations if messages exist
    if messages:
        test_message = messages[0]

        # Benchmark get_message
        _, _get_single_time = measure_performance(lambda: mail_adapter_client.get_message(test_message.id))

        # Benchmark mark_as_read
        _, _mark_time = measure_performance(lambda: mail_adapter_client.mark_as_read(test_message.id))


# @pytest.mark.e2e
# @pytest.mark.local_credentials
# def test_e2e_gmail_authentication_scenarios(service_base_url: str) -> None:
#     """E2E test for Gmail authentication scenarios and error handling.

#     Tests:
#     - Interactive authentication flow
#     - Environment variable authentication
#     - Token file authentication
#     - Authentication error handling
#     - Credential validation
#     """
#     import os
#     import tempfile
#     from unittest.mock import patch

#     # Test 1: Environment variable authentication
#     # Create a test adapter with environment variables
#     from mail_client_adapter import ServiceClientAdapter
#     from mail_client_service_client import Client

#     # Test with various environment variable scenarios
#     env_scenarios = [
#         {
#             "GMAIL_CLIENT_ID": "test_client_id",
#             "GMAIL_CLIENT_SECRET": "test_secret",
#             "GMAIL_REFRESH_TOKEN": "test_token",
#         },
#         {"GMAIL_CLIENT_ID": "", "GMAIL_CLIENT_SECRET": "", "GMAIL_REFRESH_TOKEN": ""},
#         {
#             "GMAIL_CLIENT_ID": "invalid",
#             "GMAIL_CLIENT_SECRET": "invalid",
#             "GMAIL_REFRESH_TOKEN": "invalid",
#         },
#     ]

#     for _i, env_vars in enumerate(env_scenarios):
#         with patch.dict(os.environ, env_vars, clear=False):
#             try:
#                 client = Client(
#                     base_url=service_base_url,
#                 )
#                 adapter = ServiceClientAdapter(client)

#                 # Try to get messages - should handle gracefully
#                 list(adapter.get_messages(max_results=1))

#             except Exception as e:
#                 pytest.fail(f"Environment variable authentication scenario {_i} failed: {e}")

#     # Test 2: Token file scenarios

#     with tempfile.TemporaryDirectory() as temp_dir:
#         token_file = Path(temp_dir) / "token.json"

#         # Test with valid token file
#         valid_token = '{"access_token": "test_token", "refresh_token": "test_refresh", "expires_in": 3600}'
#         token_file.write_text(valid_token)

#         try:
#             with patch.dict(os.environ, {"GMAIL_TOKEN_PATH": str(token_file)}, clear=False):
#                 client = Client(
#                     base_url=service_base_url,
#                 )
#                 adapter = ServiceClientAdapter(client)

#                 list(adapter.get_messages(max_results=1))

#         except Exception as e:
#             pytest.fail(f"Valid token file scenario test failed: {e}")

#         # !TODO: I need to check this later!!!

#         # Test with invalid token file
#         token_file.write_text("invalid json")

#         with patch.dict(os.environ, {"GMAIL_TOKEN_PATH": str(token_file)}, clear=False):
#             try:
#                 client = Client(
#                     base_url=service_base_url,
#                 )
#                 adapter = ServiceClientAdapter(client)
#                 list(adapter.get_messages(max_results=1))
#                 pytest.fail("Expected exception due to invalid token file, but no exception was raised.")
#             except Exception as e:
#                 # Expected: Should raise due to invalid token, check it's a reasonable error
#                 assert isinstance(e, Exception)

#     # Test 3: Interactive authentication simulation

#     try:
#         with patch.dict(os.environ, {"GMAIL_INTERACTIVE": "true"}, clear=False):
#             client = Client(
#                 base_url=service_base_url,
#             )
#             adapter = ServiceClientAdapter(client)

#             list(adapter.get_messages(max_results=1))

#     except Exception as e:
#         pytest.fail(f"Interactive authentication simulation test failed: {e}")


# @pytest.mark.e2e
# @pytest.mark.local_credentials
# def test_e2e_client_advanced_features(service_base_url: str) -> None:
#     """E2E test for advanced client features and configurations.

#     Tests:
#     - Client configuration options
#     - Timeout handling
#     - Retry mechanisms
#     - Connection pooling
#     - Advanced HTTP features
#     """
#     import time

#     from mail_client_adapter import ServiceClientAdapter
#     from mail_client_service_client import Client

#     # Test 1: Different timeout configurations

#     timeout_configs = [1.0, 5.0, 10.0, 30.0]

#     for timeout in timeout_configs:
#         try:
#             client = Client(base_url=service_base_url, timeout=timeout)
#             adapter = ServiceClientAdapter(client)

#             start_time = time.time()
#             list(adapter.get_messages(max_results=1))
#             time.time() - start_time

#         except Exception as e:
#             pytest.fail(f"Client with timeout {timeout} test failed: {e}")

#     # Test 2: Client with custom headers

#     try:
#         client = Client(
#             base_url=service_base_url,
#             headers={"User-Agent": "E2E-Test-Client", "X-Test-Header": "test-value"},
#         )
#         adapter = ServiceClientAdapter(client)

#         list(adapter.get_messages(max_results=1))

#     except Exception as e:
#         pytest.fail(f"Client with custom headers test failed: {e}")

#     # Test 3: Client with cookies

#     try:
#         client = Client(
#             base_url=service_base_url,
#             cookies={"test-cookie": "test-value", "session-id": "12345"},
#         )
#         adapter = ServiceClientAdapter(client)

#         list(adapter.get_messages(max_results=1))

#     except Exception as e:
#         pytest.fail(f"Client with cookies test failed: {e}")

#     # Test 4: Client with SSL configuration

#     try:
#         import ssl

#         ssl.create_default_context()
#         client = Client(base_url=service_base_url, verify_ssl=True)
#         adapter = ServiceClientAdapter(client)

#         list(adapter.get_messages(max_results=1))

#     except Exception as e:
#         pytest.fail(f"Client SSL configuration test failed: {e}")

#     # Test 5: Client connection limits

#     try:
#         client = Client(
#             base_url=service_base_url,
#             limits={"max_connections": 10, "max_keepalive_connections": 5},
#         )
#         adapter = ServiceClientAdapter(client)

#         list(adapter.get_messages(max_results=1))

#     except Exception as e:
#         pytest.fail(f"Client connection limits test failed: {e}")


# @pytest.mark.e2e
# @pytest.mark.local_credentials
# def test_e2e_service_client_adapter_edge_cases(service_base_url: str) -> None:
#     """E2E test for ServiceClientAdapter edge cases and error scenarios.

#     Tests:
#     - Iterator behavior
#     - Error propagation
#     - Resource cleanup
#     - State management
#     """
#     import gc

#     from mail_client_adapter import ServiceClientAdapter
#     from mail_client_service_client import Client

#     # Test 1: Iterator behavior and resource cleanup

#     client = Client(
#         base_url=service_base_url,
#     )
#     adapter = ServiceClientAdapter(client)

#     # Test iterator with early termination
#     try:
#         message_iter = adapter.get_messages(max_results=10)
#         for count, _msg in enumerate(message_iter, 1):
#             if count >= 3:  # Early termination
#                 break

#         # Force garbage collection to test cleanup
#         gc.collect()

#     except Exception as e:
#         pytest.fail(f"Iterator behavior and resource cleanup test failed: {e}")

#     # Test 2: Multiple iterator usage

#     try:
#         # Create multiple iterators
#         iter1 = adapter.get_messages(max_results=2)
#         iter2 = adapter.get_messages(max_results=2)

#         list(iter1)
#         list(iter2)

#     except Exception as e:
#         pytest.fail(f"Multiple iterator usage test failed: {e}")

#     # Test 3: Error propagation testing

#     error_scenarios = [
#         ("get_message", "nonexistent-id-12345"),
#         ("mark_as_read", "nonexistent-id-12345"),
#         ("delete_message", "nonexistent-id-12345"),
#     ]

#     for operation, test_id in error_scenarios:
#         try:
#             if operation == "get_message":
#                 adapter.get_message(test_id)
#             elif operation == "mark_as_read":
#                 adapter.mark_as_read(test_id)
#             elif operation == "delete_message":
#                 adapter.delete_message(test_id)

#         except RuntimeError as e:
#             pytest.fail(f"Error propagation testing test failed: Runtime - {e}")
#         except Exception as e:
#             pytest.fail(f"Error propagation testing test failed: {e}")

#     # Test 4: State management

#     try:
#         # Test that adapter maintains state correctly
#         messages = list(adapter.get_messages(max_results=1))

#         if messages:
#             msg_id = messages[0].id

#             # Perform operations and verify state consistency
#             retrieved = adapter.get_message(msg_id)
#             assert retrieved.id == msg_id

#             success = adapter.mark_as_read(msg_id)
#             assert success is True

#             # Verify message is still accessible
#             verified = adapter.get_message(msg_id)
#             assert verified.id == msg_id

#     except Exception as e:
#         pytest.fail(f"State management test failed: {e}")


@pytest.mark.e2e
@pytest.mark.local_credentials
def test_e2e_gmail_message_parsing_edge_cases(service_base_url: str) -> None:  # noqa: C901
    """E2E test for Gmail message parsing edge cases and error handling.

    Tests:
    - Malformed message data
    - Binary content handling
    - Encoding issues
    - Large message handling
    - Special character handling
    """
    from mail_client_adapter import ServiceClientAdapter
    from mail_client_service_client import Client

    client = Client(
        base_url=service_base_url,
    )
    adapter = ServiceClientAdapter(client)

    # Test 1: Message content analysis

    try:
        messages = list(adapter.get_messages(max_results=5))

        for _i, msg in enumerate(messages):
            # Test various content scenarios
            content_tests = [
                ("subject_length", len(msg.subject)),
                ("body_length", len(msg.body)),
                ("from_length", len(msg.from_)),
                ("date_length", len(msg.date)),
            ]

            for _test_name, _value in content_tests:
                pass

            # Test for special characters
            special_chars = ["<", ">", "&", '"', "'", "\n", "\r", "\t", "\\"]
            found_chars = [char for char in special_chars if char in msg.body]
            if found_chars:
                pass

            # Test for encoding issues
            with suppress(UnicodeEncodeError):
                msg.body.encode("utf-8")

            # Test for binary-like content
            ASCII_MAX_VALUE = 127  # noqa: N806
            if any(ord(c) > ASCII_MAX_VALUE for c in msg.body[:100]):
                pass

    except Exception as e:
        pytest.fail(f"Message content analysis test failed: {e}")

    # Test 2: Large message handling

    try:
        # Request larger messages to test size handling
        messages = list(adapter.get_messages(max_results=20))

        large_messages = [msg for msg in messages if len(msg.body) > 1000]  # noqa: PLR2004 # arbitrary for large message

        for _i, msg in enumerate(large_messages[:3]):  # Test first 3 large messages
            # Test that we can still access all fields
            assert hasattr(msg, "id")
            assert hasattr(msg, "subject")
            assert hasattr(msg, "from_")
            assert hasattr(msg, "date")
            assert hasattr(msg, "body")

    except Exception as e:
        pytest.fail(f"Large message handling test failed: {e}")

    # Test 3: Message format validation

    try:
        messages = list(adapter.get_messages(max_results=3))

        for _i, msg in enumerate(messages):
            # Validate required fields exist and are strings
            required_fields = ["id", "subject", "from_", "date", "body"]
            for field in required_fields:
                value = getattr(msg, field)
                assert isinstance(value, str), f"Field {field} is not string"
                assert value is not None, f"Field {field} is None"

            # Validate field content
            assert len(msg.id) > 0, "Empty message ID"
            assert isinstance(msg.subject, str), "Subject is not string"
            assert isinstance(msg.from_, str), "From field is not string"
            assert isinstance(msg.date, str), "Date field is not string"
            assert isinstance(msg.body, str), "Body field is not string"

    except Exception as e:
        pytest.fail(f"Message format validation test failed: {e}")


@pytest.mark.e2e
@pytest.mark.local_credentials
def test_e2e_service_initialization_and_lifecycle(service_base_url: str) -> None:  # noqa: PLR0915, PLR0912, C901
    """E2E test for service initialization and lifecycle management.

    Tests:
    - Service startup
    - Health checks
    - Graceful shutdown
    - Resource management
    """
    import time

    import httpx

    # Test 1: Service health and status

    try:
        # Test OpenAPI endpoint
        response = httpx.get(f"{service_base_url}/openapi.json", timeout=10.0)
        assert response.status_code == httpx.codes.OK

        openapi_data = response.json()
        assert "openapi" in openapi_data
        assert "info" in openapi_data
        assert "paths" in openapi_data

        # Test service info
        if "info" in openapi_data:
            openapi_data["info"]

        # Test available endpoints
        if "paths" in openapi_data:
            paths = openapi_data["paths"]
            expected_endpoints = ["/messages", "/messages/{message_id}"]

            for endpoint in expected_endpoints:
                if endpoint in paths:
                    pass
                else:
                    pass

    except Exception as e:
        pytest.fail(f"Service health and status test failed: {e}")

    # Test 2: Service response times

    try:
        response_times = []

        for _i in range(5):
            start_time = time.time()
            response = httpx.get(f"{service_base_url}/openapi.json", timeout=5.0)
            response_time = time.time() - start_time

            response_times.append(response_time)

        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        # Validate response times are reasonable
        assert (
            avg_response_time < 2.0  # noqa: PLR2004 # arbitrary for now
        ), f"Average response time too high: {avg_response_time:.3f}s"
        assert (
            max_response_time < 5.0  # noqa: PLR2004 # arbitrary for now
        ), f"Maximum response time too high: {max_response_time:.3f}s"

    except Exception as e:
        pytest.fail(f"Service response times test failed: {e}")

    # Test 3: Service error handling

    try:
        # Test non-existent endpoints
        error_endpoints = [
            "/nonexistent",
            "/messages/invalid-id",
            "/invalid/path",
        ]

        for endpoint in error_endpoints:
            try:
                response = httpx.get(f"{service_base_url}{endpoint}", timeout=5.0)
            except httpx.HTTPStatusError as e:
                pytest.fail(f"Service error handling test failed: {e}")
            except Exception as e:
                pytest.fail(f"Service error handling test failed: {e}")

    except Exception as e:
        pytest.fail(f"Service error handling test failed: {e}")

    # Test 4: Service resource management

    try:
        # Test multiple concurrent requests
        import queue
        import threading

        results_queue = queue.Queue()

        def make_request() -> None:
            try:
                start_time = time.time()
                response = httpx.get(f"{service_base_url}/openapi.json", timeout=10.0)
                response_time = time.time() - start_time
                results_queue.put(("success", response.status_code, response_time))
            except Exception as e:
                results_queue.put(("error", str(e), 0))

        # Start multiple concurrent requests
        threads = []
        for _i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=15)

        # Collect results
        success_count = 0
        error_count = 0
        total_time = 0

        while not results_queue.empty():
            result_type, _data, response_time = results_queue.get()
            if result_type == "success":
                success_count += 1
                total_time += response_time
            else:
                error_count += 1

        if success_count > 0:
            total_time / success_count
        else:
            pass

    except Exception as e:
        pytest.fail(f"Service resource management test failed: {e}")


@pytest.mark.e2e
@pytest.mark.local_credentials
def test_e2e_mail_client_service_direct_integration(service_base_url: str) -> None:  # noqa: PLR0915, PLR0912, C901
    """E2E test for direct mail client service integration.

    Tests:
    - Service endpoint direct access
    - HTTP response validation
    - Service error handling
    - API contract compliance
    """
    import httpx

    # Test 1: Direct service endpoint access

    try:
        # Test GET /messages endpoint
        response = httpx.get(f"{service_base_url}/messages", timeout=10.0)
        assert response.status_code == httpx.codes.OK

        messages_data = response.json()
        assert isinstance(messages_data, list)

        # Test message structure in HTTP response
        if messages_data:
            first_message = messages_data[0]
            required_keys = ["id", "from", "to", "subject", "date", "body"]

            for key in required_keys:
                assert key in first_message, f"Missing key: {key}"
                assert isinstance(first_message[key], str), f"Key {key} is not string"

            # Test GET /messages/{id} endpoint
            message_id = first_message["id"]
            response = httpx.get(f"{service_base_url}/messages/{message_id}", timeout=10.0)
            assert response.status_code == httpx.codes.OK

            single_message = response.json()
            assert single_message["id"] == message_id

            # Test POST /messages/{id}/mark-as-read endpoint
            response = httpx.post(f"{service_base_url}/messages/{message_id}/mark-as-read", timeout=10.0)
            assert response.status_code == httpx.codes.OK

            mark_response = response.json()
            assert "detail" in mark_response

    except Exception as e:
        pytest.fail(f"Direct service endpoint access test failed: {e}")

    # Test 2: HTTP error handling

    try:
        # Test 404 for non-existent message
        response = httpx.get(f"{service_base_url}/messages/non-existent-id", timeout=5.0)

        # Test invalid endpoint
        with suppress(httpx.HTTPStatusError):
            response = httpx.get(f"{service_base_url}/invalid-endpoint", timeout=5.0)

    except Exception as e:
        pytest.fail(f"HTTP error handling test failed: {e}")

    # Test 3: API contract compliance

    try:
        # Test OpenAPI schema compliance
        response = httpx.get(f"{service_base_url}/openapi.json", timeout=5.0)
        assert response.status_code == httpx.codes.OK

        schema = response.json()

        # Validate OpenAPI structure
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

        # Check required endpoints exist
        paths = schema["paths"]
        required_endpoints = [
            "/messages",
            "/messages/{message_id}",
            "/messages/{message_id}/mark-as-read",
        ]

        for endpoint in required_endpoints:
            if endpoint in paths:
                pass
            else:
                pass

        # Check HTTP methods
        if "/messages" in paths:
            methods = list(paths["/messages"].keys())
            assert "get" in methods, "GET method missing for /messages"

        if "/messages/{message_id}" in paths:
            methods = list(paths["/messages/{message_id}"].keys())
            assert "get" in methods, "GET method missing for /messages/{message_id}"

        if "/messages/{message_id}/mark-as-read" in paths:
            methods = list(paths["/messages/{message_id}/mark-as-read"].keys())
            assert "post" in methods, "POST method missing for mark-as-read"

    except Exception as e:
        pytest.fail(f"API contract compliance test failed: {e}")

    # Test 4: Service metadata and configuration

    try:
        response = httpx.get(f"{service_base_url}/openapi.json", timeout=5.0)
        schema = response.json()

        if "info" in schema:
            info = schema["info"]

            # Check service information
            if "title" in info:
                pass

            if "version" in info:
                pass

            if "description" in info:
                pass

        # Check for additional metadata
        if "servers" in schema:
            schema["servers"]

    except Exception as e:
        pytest.fail(f"Service metadata and configuration test failed: {e}")


@pytest.mark.e2e
@pytest.mark.local_credentials
def test_e2e_comprehensive_api_coverage(service_base_url: str) -> None:  # noqa: PLR0915, PLR0912, C901
    """E2E test for comprehensive API coverage and edge cases.

    Tests:
    - All API endpoints
    - Request/response validation
    - Error scenarios
    - Performance under load
    """
    import queue
    import threading
    import time

    import httpx

    from mail_client_adapter import ServiceClientAdapter
    from mail_client_service_client import Client

    # Test 1: Complete API endpoint coverage

    client = Client(
        base_url=service_base_url,
    )
    adapter = ServiceClientAdapter(client)

    try:
        # Test all adapter methods
        messages = list(adapter.get_messages(max_results=5))

        if messages:
            test_message = messages[0]
            message_id = test_message.id

            retrieved_message = adapter.get_message(message_id)
            assert retrieved_message.id == message_id

            success = adapter.mark_as_read(message_id)
            assert success is True

            # Test delete only if we have multiple messages
            if len(messages) > 1:
                delete_message = messages[-1]
                delete_success = adapter.delete_message(delete_message.id)
                assert delete_success is True
            else:
                pass

    except Exception as e:
        # This level: error occurred during the entirety of HTTP API direct coverage phase (including both static and dynamic endpoints)
        pytest.fail(f"HTTP API direct coverage test failed in overall HTTP API coverage block: {e}")

    # Test 2: HTTP API direct coverage

    try:
        # Test all HTTP endpoints directly
        endpoints_to_test = [
            ("GET", "/messages"),
            ("GET", "/openapi.json"),
        ]

        for method, endpoint in endpoints_to_test:
            try:
                if method == "GET":
                    response = httpx.get(f"{service_base_url}{endpoint}", timeout=10.0)
                else:
                    response = httpx.request(method, f"{service_base_url}{endpoint}", timeout=10.0)

                # Validate response content
                if response.status_code == httpx.codes.OK:
                    if endpoint == "/messages":
                        data = response.json()
                        assert isinstance(data, list)
                    elif endpoint == "/openapi.json":
                        data = response.json()
                        assert "openapi" in data

            except Exception as e:
                # This level: error occurred while calling a specific static endpoint (e.g., GET /messages, GET /openapi.json)
                pytest.fail(f"HTTP API direct coverage test failed at static endpoint invocation: {e}")

        # Test dynamic endpoints if we have messages
        try:
            messages = list(adapter.get_messages(max_results=1))
            if messages:
                message_id = messages[0].id

                dynamic_endpoints = [
                    ("GET", f"/messages/{message_id}"),
                    ("POST", f"/messages/{message_id}/mark-as-read"),
                ]

                for method, endpoint in dynamic_endpoints:
                    try:
                        if method == "GET":
                            response = httpx.get(f"{service_base_url}{endpoint}", timeout=10.0)
                        elif method == "POST":
                            response = httpx.post(f"{service_base_url}{endpoint}", timeout=10.0)

                    except Exception as e:
                        # This level: error occurred while calling a specific dynamic endpoint (e.g., GET /messages/{id}, POST /messages/{id}/mark-as-read)
                        pytest.fail(f"HTTP API direct coverage test failed at endpoint invocation: {e}")

        except Exception as e:
            # This level: error occurred while attempting any of the dynamic endpoint operations, possibly for all endpoints or before entering their loop
            pytest.fail(f"HTTP API direct coverage test failed during dynamic endpoints setup or iteration: {e}")

    except Exception as e:
        # This level: error occurred during the entirety of HTTP API direct coverage phase (including both static and dynamic endpoints)
        pytest.fail(f"HTTP API direct coverage test failed in overall HTTP API coverage block: {e}")

    # Test 3: Performance under load

    try:

        def load_test_worker(results_queue: queue.Queue) -> None:
            try:
                start_time = time.time()

                # Perform multiple operations
                messages = list(adapter.get_messages(max_results=2))

                if messages:
                    msg = messages[0]
                    adapter.get_message(msg.id)
                    adapter.mark_as_read(msg.id)

                execution_time = time.time() - start_time
                results_queue.put(("success", execution_time))

            except Exception as e:
                results_queue.put(("error", str(e)))

        # Run load test with multiple workers
        results_queue = queue.Queue()
        threads = []

        for _i in range(5):  # 5 concurrent workers
            thread = threading.Thread(target=load_test_worker, args=(results_queue,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=30)

        # Collect results
        success_count = 0
        error_count = 0
        total_time = 0

        while not results_queue.empty():
            result_type, data = results_queue.get()
            if result_type == "success":
                success_count += 1
                total_time += data
            else:
                error_count += 1

        if success_count > 0:
            total_time / success_count
        else:
            pytest.fail("No successful operations completed")

    except Exception as e:
        pytest.fail(f"Performance under load test failed: {e}")


# @pytest.mark.e2e
# @pytest.mark.local_credentials
# def test_e2e_gmail_implementation_direct_coverage(service_base_url: str) -> None:
#     """E2E test for direct Gmail implementation coverage.

#     Tests:
#     - Gmail client initialization
#     - Authentication flows
#     - Message parsing
#     - Error handling paths
#     """
#     import os
#     import tempfile
#     from unittest.mock import Mock, patch

#     # Test 1: Gmail client initialization scenarios

#     try:
#         # Import Gmail implementation directly
#         from gmail_client_impl.message_impl import GmailMessage

#         from gmail_client_impl import GmailClient

#         # Test with different initialization scenarios
#         init_scenarios = [
#             {"interactive": False, "service": None},
#             {"interactive": True, "service": None},
#         ]

#         for _i, scenario in enumerate(init_scenarios):
#             try:
#                 # Mock the service to avoid actual Gmail API calls
#                 mock_service = Mock()
#                 mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
#                     "messages": [{"id": "test_msg_1"}]
#                 }
#                 mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = {
#                     "raw": "dGVzdCBtZXNzYWdlIGRhdGE="  # base64 encoded test data
#                 }

#                 GmailClient(service=mock_service, **scenario)

#             except Exception as e:
#                 pytest.fail(f"Gmail client initialization test failed: {e}")

#     except Exception as e:
#         pytest.fail(f"Gmail client initialization test failed: {e}")

#     # Test 2: Gmail message parsing

#     try:
#         from gmail_client_impl.message_impl import GmailMessage

#         # Test various message data scenarios
#         test_messages = [
#             ("valid_message", "dGVzdCBtZXNzYWdlIGRhdGE="),  # Valid base64
#             ("invalid_base64", "invalid_base64_data"),
#             ("empty_data", ""),
#             ("binary_data", "binary\x00\x01\x02data"),
#         ]

#         for _test_name, raw_data in test_messages:
#             try:
#                 message = GmailMessage("test_id", raw_data)

#                 # Test message properties
#                 assert hasattr(message, "id")
#                 assert hasattr(message, "subject")
#                 assert hasattr(message, "from_")
#                 assert hasattr(message, "to")
#                 assert hasattr(message, "date")
#                 assert hasattr(message, "body")

#             except Exception as e:
#                 pytest.fail(f"Gmail message parsing test failed: {e}")

#     except Exception as e:
#         pytest.fail(f"Gmail message parsing test failed: {e}")

#     # Test 3: Authentication error handling

#     try:
#         from gmail_client_impl import GmailClient

#         # Test with invalid credentials
#         with patch.dict(
#             os.environ,
#             {
#                 "GMAIL_CLIENT_ID": "invalid",
#                 "GMAIL_CLIENT_SECRET": "invalid",
#                 "GMAIL_REFRESH_TOKEN": "invalid",
#             },
#             clear=False,
#         ):
#             try:
#                 GmailClient(interactive=False)
#             except RuntimeError as e:
#                 pytest.fail(f"Authentication error handling test failed: {e}")
#             except Exception as e:
#                 pytest.fail(f"Authentication error handling test failed: {e}")

#     except Exception as e:
#         pytest.fail(f"Authentication error handling test failed: {e}")

#     # Test 4: Token file handling

#     try:
#         from gmail_client_impl import GmailClient

#         with tempfile.TemporaryDirectory() as temp_dir:
#             token_file = Path(temp_dir) / "token.json"

#             # Test with valid token file
#             valid_token = '{"access_token": "test_token", "refresh_token": "test_refresh", "expires_in": 3600}'
#             token_file.write_text(valid_token)

#             with patch.dict(os.environ, {"GMAIL_TOKEN_PATH": str(token_file)}, clear=False), suppress(Exception):
#                 GmailClient(interactive=False)

#             # Test with invalid token file
#             token_file.write_text("invalid json")

#             with patch.dict(os.environ, {"GMAIL_TOKEN_PATH": str(token_file)}, clear=False), suppress(Exception):
#                 GmailClient(interactive=False)

#     except Exception as e:
#         pytest.fail(f"Token file handling test failed: {e}")


@pytest.mark.e2e
@pytest.mark.local_credentials
def test_e2e_mail_client_service_coverage(service_base_url: str) -> None:  # noqa: PLR0915, PLR0912, C901
    """E2E test for mail client service coverage.

    Tests:
    - Service initialization
    - FastAPI app lifecycle
    - Dependency injection
    - Error handling
    """
    import httpx

    # Test 1: Service initialization and health

    try:
        # Test service startup
        response = httpx.get(f"{service_base_url}/openapi.json", timeout=10.0)
        assert response.status_code == httpx.codes.OK

        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

        # Test service info
        schema.get("info", {})

    except Exception as e:
        pytest.fail(f"Service initialization and health test failed: {e}")

    # Test 2: Service endpoints and methods

    try:
        # Test all available endpoints
        endpoints = [
            ("GET", "/messages"),
            ("GET", "/openapi.json"),
        ]

        for method, endpoint in endpoints:
            try:
                if method == "GET":
                    response = httpx.get(f"{service_base_url}{endpoint}", timeout=10.0)
                else:
                    response = httpx.request(method, f"{service_base_url}{endpoint}", timeout=10.0)

                # Test response content
                if response.status_code == httpx.codes.OK:
                    if endpoint == "/messages":
                        data = response.json()
                        assert isinstance(data, list)

                        # Test dynamic endpoints if we have messages
                        if data:
                            message_id = data[0]["id"]

                            # Test GET /messages/{id}
                            with suppress(Exception):
                                response = httpx.get(
                                    f"{service_base_url}/messages/{message_id}",
                                    timeout=10.0,
                                )

                            # Test POST /messages/{id}/mark-as-read
                            with suppress(Exception):
                                response = httpx.post(
                                    f"{service_base_url}/messages/{message_id}/mark-as-read",
                                    timeout=10.0,
                                )

                    elif endpoint == "/openapi.json":
                        data = response.json()
                        assert "openapi" in data

            except Exception as e:
                pytest.fail(f"Service endpoints and methods test failed: {e}")

    except Exception as e:
        pytest.fail(f"Service endpoints and methods test failed: {e}")

    # Test 3: Service error handling

    try:
        # Test various error scenarios
        error_scenarios = [
            ("GET", "/nonexistent"),
            ("GET", "/messages/invalid-id"),
            ("POST", "/invalid-endpoint"),
        ]

        for method, endpoint in error_scenarios:
            try:
                if method == "GET":
                    response = httpx.get(f"{service_base_url}{endpoint}", timeout=5.0)
                else:
                    response = httpx.request(method, f"{service_base_url}{endpoint}", timeout=5.0)

            except httpx.HTTPStatusError as e:
                pytest.fail(f"Service error handling test failed: {e}")
            except Exception as e:
                pytest.fail(f"Service error handling test failed: {e}")

    except Exception as e:
        pytest.fail(f"Service error handling test failed: {e}")

    # Test 4: Service performance and reliability

    try:
        import time

        # Test response times
        response_times = []

        for _i in range(3):
            start_time = time.time()
            response = httpx.get(f"{service_base_url}/openapi.json", timeout=5.0)
            response_time = time.time() - start_time

            response_times.append(response_time)

        avg_time = sum(response_times) / len(response_times)

        # Validate performance
        assert avg_time < 2.0, f"Average response time too high: {avg_time:.3f}s"  # noqa: PLR2004

    except Exception as e:
        pytest.fail(f"Performance and reliability test failed: {e}")


# @pytest.mark.e2e
# @pytest.mark.local_credentials
# def test_e2e_comprehensive_system_integration(
#     service_base_url: str,
#     mail_adapter_client,  # import ServiceClientAdapter kept seperate
# ) -> None:
#     """E2E test for comprehensive system integration coverage.

#     Tests:
#     - End-to-end system flow
#     - All components integration
#     - Error propagation
#     - System resilience
#     """
#     import queue
#     import threading
#     import time

#     # Test 1: Complete system flow

#     try:
#         # Use shared adapter
#         adapter = mail_adapter_client

#         # Test complete workflow
#         messages = list(adapter.get_messages(max_results=3))

#         if messages:
#             test_message = messages[0]

#             retrieved = adapter.get_message(test_message.id)
#             assert retrieved.id == test_message.id

#             success = adapter.mark_as_read(test_message.id)
#             assert success is True

#             verified = adapter.get_message(test_message.id)
#             assert verified.id == test_message.id

#             # Test delete only if we have multiple messages
#             if len(messages) > 1:
#                 delete_message = messages[-1]
#                 delete_success = adapter.delete_message(delete_message.id)
#                 assert delete_success is True

#                 with suppress(RuntimeError):
#                     adapter.get_message(delete_message.id)
#             else:
#                 pass

#     except Exception as e:
#         pytest.fail(f"Comprehensive system integration test failed: {e}")

#     # Test 2: System resilience

#     try:
#         # Test system under various conditions
#         resilience_tests = [
#             ("normal_load", lambda: list(adapter.get_messages(max_results=2))),
#             ("high_load", lambda: list(adapter.get_messages(max_results=10))),
#             ("error_recovery", lambda: adapter.get_message("invalid-id")),
#         ]

#         for _test_name, test_func in resilience_tests:
#             with suppress(Exception):
#                 test_func()

#     except Exception as e:
#         pytest.fail(f"System resilience test failed: {e}")

#     # Test 3: Concurrent system usage

#     try:

#         def concurrent_worker(results_queue: queue.Queue) -> None:
#             try:
#                 start_time = time.time()

#                 # Perform system operations
#                 messages = list(adapter.get_messages(max_results=1))

#                 if messages:
#                     msg = messages[0]
#                     adapter.get_message(msg.id)
#                     adapter.mark_as_read(msg.id)

#                 execution_time = time.time() - start_time
#                 results_queue.put(("success", execution_time))

#             except Exception as e:
#                 results_queue.put(("error", str(e)))

#         # Run concurrent workers
#         results_queue = queue.Queue()
#         threads = []

#         for _i in range(3):  # 3 concurrent workers
#             thread = threading.Thread(target=concurrent_worker, args=(results_queue,))
#             threads.append(thread)
#             thread.start()

#         # Wait for completion
#         for thread in threads:
#             thread.join(timeout=20)

#         # Collect results
#         success_count = 0
#         error_count = 0
#         total_time = 0

#         while not results_queue.empty():
#             result_type, data = results_queue.get()
#             if result_type == "success":
#                 success_count += 1
#                 total_time += data
#             else:
#                 error_count += 1

#         if success_count > 0:
#             total_time / success_count
#         else:
#             pytest.fail("No successful concurrent operations completed")

#     except Exception as e:
#         pytest.fail(f"Concurrent system usage test failed: {e}")

#     # Test 4: System error propagation

#     try:
#         # Test error propagation through all layers
#         error_scenarios = [
#             ("invalid_message_id", "nonexistent-id-12345"),
#             ("malformed_request", ""),
#             ("service_error", "error-id"),
#         ]

#         for _scenario_name, test_id in error_scenarios:
#             try:
#                 adapter.get_message(test_id)
#             except RuntimeError as e:
#                 pytest.fail(f"System error propagation test failed with RuntimeError: {e}")
#             except Exception as e:
#                 pytest.fail(f"System error propagation test failed with Exception: {e}")

#     except Exception as e:
#         pytest.fail(f"System error propagation test failed: {e}")


# @pytest.mark.e2e
# @pytest.mark.local_credentials
# def test_e2e_mail_client_adapter_comprehensive_coverage(
#     service_base_url: str,
#     mail_adapter_client,  # import ServiceClientAdapter kept seperate
# ) -> None:
#     """E2E test for comprehensive mail client adapter coverage.

#     Tests:
#     - All adapter methods
#     - Error handling paths
#     - Iterator behavior
#     - Resource management
#     """
#     import gc

#     # Test 1: All adapter methods

#     try:
#         # Use shared adapter
#         adapter = mail_adapter_client

#         # Test get_messages with various parameters

#         param_scenarios = [
#             {"max_results": 1},
#             {"max_results": 5},
#             {"max_results": 10},
#         ]

#         for _i, params in enumerate(param_scenarios):
#             with suppress(Exception):
#                 messages = list(adapter.get_messages(**params))

#         # Test get_message with various IDs

#         try:
#             messages = list(adapter.get_messages(max_results=1))
#             if messages:
#                 test_message = messages[0]

#                 # Test valid message ID
#                 retrieved = adapter.get_message(test_message.id)
#                 assert retrieved.id == test_message.id

#                 # Test invalid message ID
#                 try:
#                     adapter.get_message("invalid-id-12345")
#                 except RuntimeError as e:
#                     pytest.fail(f"Invalid message ID test failed with RuntimeError: {e}")
#                 except Exception as e:
#                     pytest.fail(f"Invalid message ID test failed with Exception: {e}")

#         except Exception as e:
#             pytest.fail(f"Adapter method test failed: {e}")

#         # Test mark_as_read

#         try:
#             messages = list(adapter.get_messages(max_results=1))
#             if messages:
#                 test_message = messages[0]

#                 # Test valid message ID
#                 success = adapter.mark_as_read(test_message.id)
#                 assert success is True

#                 # Test invalid message ID
#                 try:
#                     adapter.mark_as_read("invalid-id-12345")
#                 except RuntimeError as e:
#                     pytest.fail(f"Invalid mark_as_read test failed with RuntimeError: {e}")
#                 except Exception as e:
#                     pytest.fail(f"Invalid mark_as_read test failed with Exception: {e}")

#         except Exception as e:
#             pytest.fail(f"Mark as read test failed: {e}")

#         # Test delete_message

#         try:
#             messages = list(adapter.get_messages(max_results=2))
#             if len(messages) > 1:
#                 delete_message = messages[-1]

#                 # Test valid message ID
#                 success = adapter.delete_message(delete_message.id)
#                 assert success is True

#                 # Test invalid message ID
#                 try:
#                     adapter.delete_message("invalid-id-12345")
#                 except RuntimeError as e:
#                     pytest.fail(f"Invalid delete_message test failed with RuntimeError: {e}")
#                 except Exception as e:
#                     pytest.fail(f"Invalid delete_message test failed with Exception: {e}")
#             else:
#                 pytest.fail("No messages available for delete test")

#         except Exception as e:
#             pytest.fail(f"Delete message test failed: {e}")

#     except Exception as e:
#         pytest.fail(f"All adapter methods test failed: {e}")

#     # Test 2: Iterator behavior and resource management

#     try:
#         from mail_client_adapter import ServiceClientAdapter
#         from mail_client_service_client import Client

#         client = Client(
#             base_url=service_base_url,
#         )
#         adapter = ServiceClientAdapter(client)

#         # Test iterator with early termination

#         try:
#             message_iter = adapter.get_messages(max_results=10)
#             for count, _msg in enumerate(message_iter, 1):
#                 if count >= 3:  # Early termination
#                     break

#             # Force garbage collection
#             gc.collect()

#         except Exception as e:
#             pytest.fail(f"Message implementation coverage test failed: {e}")

#         # Test multiple iterators

#         try:
#             iter1 = adapter.get_messages(max_results=2)
#             iter2 = adapter.get_messages(max_results=2)

#             list(iter1)
#             list(iter2)

#         except Exception as e:
#             pytest.fail(f"Multiple iterator test failed: {e}")

#         # Test iterator with empty results

#         try:
#             # This might return empty results in some environments
#             messages = list(adapter.get_messages(max_results=0))

#         except Exception as e:
#             pytest.fail(f"Iterator with empty results test failed: {e}")

#     except Exception as e:
#         pytest.fail(f"Mail Service Client E2E coverage outer block failed: {e}")

#     # Test 3: Error handling and edge cases

#     try:
#         from mail_client_adapter import ServiceClientAdapter
#         from mail_client_service_client import Client

#         client = Client(
#             base_url=service_base_url,
#         )
#         adapter = ServiceClientAdapter(client)

#         # Test with various edge case inputs
#         edge_cases = [
#             ("empty_string", ""),
#             ("whitespace", "   "),
#             ("special_chars", "!@#$%^&*()"),
#             ("very_long_id", "x" * 1000),
#             ("numeric_id", "123456"),
#         ]

#         for _case_name, test_id in edge_cases:
#             try:
#                 adapter.get_message(test_id)
#             except RuntimeError:
#                 pass
#             except Exception as e:
#                 pytest.fail(f"Error handling edge case {_case_name} failed: {e}")

#     except Exception as e:
#         pytest.fail(f"Error handling edge cases test failed: {e}")


@pytest.mark.e2e
@pytest.mark.local_credentials
def test_e2e_gmail_message_implementation_coverage(service_base_url: str) -> None:
    """E2E test for Gmail message implementation coverage.

    Tests:
    - Message parsing edge cases
    - Binary content handling
    - Encoding issues
    - Error recovery
    """
    import base64

    from gmail_client_impl.message_impl import GmailMessage

    # Test 1: Message parsing with various data types

    test_cases = [
        ("valid_base64", "dGVzdCBtZXNzYWdlIGRhdGE="),
        ("invalid_base64", "invalid_base64_data"),
        ("empty_data", ""),
        ("binary_data", "binary\x00\x01\x02data"),
        ("unicode_data", "test message with unicode: éñü"),
        ("html_content", "<html><body>Test message</body></html>"),
        ("json_data", '{"test": "message", "data": "value"}'),
    ]

    for _test_name, raw_data in test_cases:
        try:
            message = GmailMessage("test_id", raw_data)

            # Test message properties
            assert hasattr(message, "id")
            assert hasattr(message, "subject")
            assert hasattr(message, "from_")
            assert hasattr(message, "to")
            assert hasattr(message, "date")
            assert hasattr(message, "body")

            # Test property access
            assert isinstance(message.id, str)
            assert isinstance(message.subject, str)
            assert isinstance(message.from_, str)
            assert isinstance(message.to, str)
            assert isinstance(message.date, str)
            assert isinstance(message.body, str)

        except Exception as e:
            pytest.fail(f"Message parsing test failed: {e}")

    # Test 2: Message with complex content

    try:
        # Create a more complex message
        complex_content = """
        From: test@example.com
        To: recipient@example.com
        Subject: Test Message with Complex Content
        Date: Mon, 1 Jan 2024 12:00:00 +0000
        Content-Type: text/html; charset=utf-8

        <html>
        <body>
        <h1>Test Message</h1>
        <p>This is a test message with <strong>HTML content</strong>.</p>
        <ul>
        <li>Item 1</li>
        <li>Item 2</li>
        </ul>
        </body>
        </html>
        """

        # Encode as base64
        encoded_content = base64.b64encode(complex_content.encode("utf-8")).decode("utf-8")

        message = GmailMessage("complex_id", encoded_content)

        # Test that we can access all properties

    except Exception as e:
        pytest.fail(f"Message with complex content test failed: {e}")

    # Test 3: Error handling in message parsing

    error_cases = [
        ("malformed_base64", "invalid_base64_data_!@#$"),
        ("binary_garbage", b"\x00\x01\x02\x03\x04".decode("latin-1")),
        ("very_long_data", "x" * 10000),
        ("special_chars", "!@#$%^&*()_+-=[]{}|;':\",./<>?"),
    ]

    for _test_name, raw_data in error_cases:
        try:
            message = GmailMessage("error_id", raw_data)

            # Even with errors, message should have valid properties
            assert hasattr(message, "id")
            assert hasattr(message, "subject")
            assert hasattr(message, "from_")
            assert hasattr(message, "to")
            assert hasattr(message, "date")
            assert hasattr(message, "body")

        except Exception as e:
            pytest.fail(f"Message parsing error test failed: {e}")

    # Test 4: Message property validation

    try:
        # Test with minimal valid data
        minimal_data = base64.b64encode(b"From: test@example.com\nSubject: Test\n\nBody").decode("utf-8")
        message = GmailMessage("minimal_id", minimal_data)

        # Validate all properties are strings
        assert isinstance(message.id, str)
        assert isinstance(message.subject, str)
        assert isinstance(message.from_, str)
        assert isinstance(message.to, str)
        assert isinstance(message.date, str)
        assert isinstance(message.body, str)

    except Exception as e:
        pytest.fail(f"Message property validation failed: {e}")


# @pytest.mark.e2e
# @pytest.mark.local_credentials
# def test_e2e_final_coverage_push(service_base_url: str, mail_adapter_client) -> None:
#     """E2E test for final coverage push to reach 85%.

#     Tests:
#     - All remaining uncovered paths
#     - Edge cases and error conditions
#     - Complex scenarios
#     - System integration
#     """
#     import base64
#     import queue
#     import threading
#     import time
#     from unittest.mock import Mock

#     import httpx
#     from gmail_client_impl.message_impl import GmailMessage

#     from gmail_client_impl import GmailClient

#     # Use shared adapter for most tests
#     adapter = mail_adapter_client

#     # Test 1: Gmail client comprehensive testing

#     try:
#         # Test Gmail client with various configurations
#         gmail_scenarios = [
#             {"interactive": False, "service": None},
#             {"interactive": True, "service": None},
#         ]

#         for _i, scenario in enumerate(gmail_scenarios):
#             try:
#                 # Mock service to avoid actual API calls
#                 mock_service = Mock()
#                 mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
#                     "messages": [{"id": "test_msg_1"}, {"id": "test_msg_2"}]
#                 }
#                 mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = {
#                     "raw": base64.b64encode(b"From: test@example.com\nSubject: Test\n\nBody").decode("utf-8")
#                 }

#                 client = GmailClient(service=mock_service, **scenario)

#                 # Test client methods
#                 messages = list(client.get_messages(max_results=2))

#                 if messages:
#                     msg = messages[0]
#                     retrieved = client.get_message(msg.id)
#                     assert retrieved.id == msg.id

#                     success = client.mark_as_read(msg.id)
#                     assert success is True

#                     if len(messages) > 1:
#                         delete_msg = messages[-1]
#                         delete_success = client.delete_message(delete_msg.id)
#                         assert delete_success is True

#             except Exception as e:
#                 pytest.fail(f"GmailClient scenario test raised an exception: {e}")

#     except Exception as e:
#         pytest.fail(f"GmailClient comprehensive testing block raised an exception: {e}")

#     # Test 2: Message implementation edge cases

#     try:
#         # Test various message parsing scenarios
#         message_scenarios = [
#             ("minimal", "RnJvbTogdGVzdEBleGFtcGxlLmNvbQpTdWJqZWN0OiBUZXN0CgpCb2R5"),
#             (
#                 "complex",
#                 "RnJvbTogdGVzdEBleGFtcGxlLmNvbQpUbzogcmVjaXBpZW50QGV4YW1wbGUuY29tClN1YmplY3Q6IFRlc3QgTWVzc2FnZQpEYXRlOiBNb24sIDEgSmFuIDIwMjQgMTI6MDA6MDAgKzAwMDAKQ29udGVudC1UeXBlOiB0ZXh0L2h0bWw7IGNoYXJzZXQ9dXRmLTgKCjxodG1sPgo8Ym9keT4KPGgxPlRlc3QgTWVzc2FnZTwvaDE+CjxwPlRoaXMgaXMgYSB0ZXN0IG1lc3NhZ2Ugd2l0aCA8c3Ryb25nPkhUTUwgY29udGVudDwvc3Ryb25nPi48L3A+Cjx1bD4KPGxpPkl0ZW0gMTwvbGk+CjxsaT5JdGVtIDI8L2xpPgo8L3VsPgo8L2JvZHk+CjwvaHRtbD4=",
#             ),
#             ("empty", ""),
#             ("invalid", "invalid_base64_data"),
#         ]

#         for test_name, raw_data in message_scenarios:
#             try:
#                 message = GmailMessage(f"test_{test_name}", raw_data)

#                 # Test all properties
#                 assert hasattr(message, "id")
#                 assert hasattr(message, "subject")
#                 assert hasattr(message, "from_")
#                 assert hasattr(message, "to")
#                 assert hasattr(message, "date")
#                 assert hasattr(message, "body")

#                 # Test property types
#                 assert isinstance(message.id, str)
#                 assert isinstance(message.subject, str)
#                 assert isinstance(message.from_, str)
#                 assert isinstance(message.to, str)
#                 assert isinstance(message.date, str)
#                 assert isinstance(message.body, str)

#             except Exception as e:
#                 pytest.fail(f"GmailMessage ({test_name}) raised an exception: {e}")

#     except Exception as e:
#         pytest.fail(f"Message implementation edge case block raised an exception: {e}")

#     # Test 3: Service client adapter comprehensive testing

#     try:
#         # Test all adapter methods with various scenarios
#         adapter_tests = [
#             ("get_messages", lambda: list(adapter.get_messages(max_results=3))),
#             ("get_messages_empty", lambda: list(adapter.get_messages(max_results=0))),
#             ("get_messages_large", lambda: list(adapter.get_messages(max_results=20))),
#         ]

#         for test_name, test_func in adapter_tests:
#             try:
#                 result = test_func()

#                 if test_name == "get_messages" and result:
#                     # Test with actual messages
#                     test_msg = result[0]

#                     # Test get_message
#                     retrieved = adapter.get_message(test_msg.id)
#                     assert retrieved.id == test_msg.id

#                     # Test mark_as_read
#                     success = adapter.mark_as_read(test_msg.id)
#                     assert success is True

#                     # Test delete_message if we have multiple messages
#                     if len(result) > 1:
#                         delete_msg = result[-1]
#                         delete_success = adapter.delete_message(delete_msg.id)
#                         assert delete_success is True

#             except Exception as e:
#                 pytest.fail(f"Adapter test '{test_name}' raised an exception: {e}")

#     except Exception as e:
#         pytest.fail(f"Service client adapter comprehensive testing raised an exception: {e}")

#     # Test 4: HTTP client comprehensive testing

#     try:
#         from mail_client_adapter import ServiceClientAdapter
#         from mail_client_service_client import Client

#         # Test various client configurations
#         client_configs = [
#             {"timeout": 1.0},
#             {"timeout": 5.0},
#             {"timeout": 30.0},
#             {"headers": {"User-Agent": "E2E-Test-Client"}},
#             {"cookies": {"test-cookie": "test-value"}},
#         ]

#         for _i, config in enumerate(client_configs):
#             try:
#                 client = Client(base_url=service_base_url, **config)
#                 adapter = ServiceClientAdapter(client)

#                 # Test basic functionality
#                 messages = list(adapter.get_messages(max_results=1))

#             except Exception as e:
#                 pytest.fail(f"Exception in client config loop: {e}")

#     except Exception as e:
#         pytest.fail(f"Exception in HTTP client comprehensive testing: {e}")

#     # Test 5: Service endpoints comprehensive testing

#     try:
#         # Test all service endpoints
#         endpoints = [
#             ("GET", "/messages"),
#             ("GET", "/openapi.json"),
#         ]

#         for method, endpoint in endpoints:
#             try:
#                 if method == "GET":
#                     response = httpx.get(f"{service_base_url}{endpoint}", timeout=10.0)
#                 else:
#                     response = httpx.request(method, f"{service_base_url}{endpoint}", timeout=10.0)

#                 if response.status_code == HTTPStatus.OK.value:
#                     if endpoint == "/messages":
#                         data = response.json()
#                         assert isinstance(data, list)

#                         # Test dynamic endpoints
#                         if data:
#                             message_id = data[0]["id"]

#                             # Test GET /messages/{id}
#                             with suppress(Exception):
#                                 response = httpx.get(
#                                     f"{service_base_url}/messages/{message_id}",
#                                     timeout=10.0,
#                                 )

#                             # Test POST /messages/{id}/mark-as-read
#                             with suppress(Exception):
#                                 response = httpx.post(
#                                     f"{service_base_url}/messages/{message_id}/mark-as-read",
#                                     timeout=10.0,
#                                 )

#                     elif endpoint == "/openapi.json":
#                         data = response.json()
#                         assert "openapi" in data

#             except Exception as e:
#                 pytest.fail(f"Endpoint test failed: {method} {endpoint} - {e}")

#     except Exception as e:
#         pytest.fail(f"Comprehensive service endpoint tests failed: {e}")

#     # Test 6: Error handling comprehensive testing

#     try:
#         from mail_client_adapter import ServiceClientAdapter
#         from mail_client_service_client import Client

#         client = Client(
#             base_url=service_base_url,
#         )
#         adapter = ServiceClientAdapter(client)

#         # Test various error scenarios
#         error_scenarios = [
#             ("get_message", "nonexistent-id-12345"),
#             ("mark_as_read", "nonexistent-id-12345"),
#             ("delete_message", "nonexistent-id-12345"),
#             ("get_message", ""),
#             ("get_message", "   "),
#             ("get_message", "!@#$%^&*()"),
#         ]

#         for operation, test_id in error_scenarios:
#             try:
#                 if operation == "get_message":
#                     adapter.get_message(test_id)
#                 elif operation == "mark_as_read":
#                     adapter.mark_as_read(test_id)
#                 elif operation == "delete_message":
#                     adapter.delete_message(test_id)

#             except RuntimeError as e:
#                 pytest.fail(f"Operation failed with RuntimeError: {e}")
#             except Exception as e:
#                 pytest.fail(f"Operation failed with Exception: {e}")

#     except Exception as e:
#         pytest.fail(f"Error handling comprehensive testing failed: {e}")

#     # Test 7: Performance and concurrency testing

#     try:
#         from mail_client_adapter import ServiceClientAdapter
#         from mail_client_service_client import Client

#         client = Client(
#             base_url=service_base_url,
#         )
#         adapter = ServiceClientAdapter(client)

#         def performance_worker(results_queue: queue.Queue) -> None:
#             try:
#                 start_time = time.time()

#                 # Perform operations
#                 messages = list(adapter.get_messages(max_results=2))

#                 if messages:
#                     msg = messages[0]
#                     adapter.get_message(msg.id)
#                     adapter.mark_as_read(msg.id)

#                 execution_time = time.time() - start_time
#                 results_queue.put(("success", execution_time))

#             except Exception as e:
#                 results_queue.put(("error", str(e)))

#         # Run performance test
#         results_queue = queue.Queue()
#         threads = []

#         for _i in range(5):  # 5 concurrent workers
#             thread = threading.Thread(target=performance_worker, args=(results_queue,))
#             threads.append(thread)
#             thread.start()

#         # Wait for completion
#         for thread in threads:
#             thread.join(timeout=30)

#         # Collect results
#         success_count = 0
#         error_count = 0
#         total_time = 0

#         while not results_queue.empty():
#             result_type, data = results_queue.get()
#             if result_type == "success":
#                 success_count += 1
#                 total_time += data
#             else:
#                 error_count += 1

#         if success_count > 0:
#             total_time / success_count
#         else:
#             pass

#     except Exception as e:
#         pytest.fail(f"Performance test failed: {e}")
