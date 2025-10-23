"""Unit tests for mail client service API endpoints."""

from collections.abc import Callable
from unittest.mock import Mock

from fastapi.testclient import TestClient


def test_list_messages_success(
    client: TestClient,
    mock_mail_client: Mock,
    create_mock_message: Callable[..., Mock],
    http_status: type,
) -> None:
    """Test successful retrieval of messages."""
    # Arrange
    NUM_OF_MESSAGES = 3  # noqa: N806
    sample_messages = [
        create_mock_message(
            "msg_001",
            "sender1@example.com",
            "recipient@example.com",
            "Test Subject 1",
            "2024-01-01T10:00:00Z",
            "This is the first test message body.",
        ),
        create_mock_message(
            "msg_002",
            "sender2@example.com",
            "recipient@example.com",
            "Test Subject 2",
            "2024-01-02T11:00:00Z",
            "This is the second test message body.",
        ),
        create_mock_message(
            "msg_003",
            "sender3@example.com",
            "recipient@example.com",
            "Test Subject 3",
            "2024-01-03T12:00:00Z",
            "This is the third test message body.",
        ),
    ]
    mock_mail_client.get_messages.return_value = sample_messages

    # Act
    response = client.get("/messages")

    # Assert
    assert http_status(response.status_code) == http_status.OK  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()

    assert len(data) == NUM_OF_MESSAGES
    assert data[0]["id"] == "msg_001"
    assert data[0]["from"] == "sender1@example.com"
    assert data[0]["to"] == "recipient@example.com"
    assert data[0]["subject"] == "Test Subject 1"
    assert data[0]["date"] == "2024-01-01T10:00:00Z"
    assert data[0]["body"] == "This is the first test message body."

    assert data[1]["id"] == "msg_002"
    assert data[2]["id"] == "msg_003"

    # Verify the mock was called correctly
    mock_mail_client.get_messages.assert_called_once()


def test_list_messages_empty_list(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test when no messages are returned."""
    # Arrange
    mock_mail_client.get_messages.return_value = []

    # Act
    response = client.get("/messages")

    # Assert
    assert http_status(response.status_code) == http_status.OK  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data == []


def test_list_messages_single_message(
    client: TestClient,
    mock_mail_client: Mock,
    create_mock_message: Callable[..., Mock],
    http_status: type,
) -> None:
    """Test with a single message."""
    # Arrange
    single_message = create_mock_message(
        "single_msg",
        "single@example.com",
        "recipient@example.com",
        "Single Message",
        "2024-01-01T10:00:00Z",
        "Single message body.",
    )
    mock_mail_client.get_messages.return_value = [single_message]

    # Act
    response = client.get("/messages")

    # Assert
    assert http_status(response.status_code) == http_status.OK  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "single_msg"
    assert data[0]["from"] == "single@example.com"


def test_list_messages_client_exception(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test when the mail client raises an exception."""
    # Arrange
    mock_mail_client.get_messages.side_effect = Exception(
        "Mail client connection failed",
    )

    # Act
    response = client.get("/messages")

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert "detail" in data
    assert "Mail client connection failed" in data["detail"]


def test_list_messages_client_runtime_error(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test when the mail client raises a RuntimeError."""
    # Arrange
    mock_mail_client.get_messages.side_effect = RuntimeError(
        "Authentication failed",
    )

    # Act
    response = client.get("/messages")

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == "Authentication failed"


def test_list_messages_client_value_error(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test when the mail client raises a ValueError."""
    # Arrange
    mock_mail_client.get_messages.side_effect = ValueError("Invalid configuration")

    # Act
    response = client.get("/messages")

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == "Invalid configuration"


def test_list_messages_with_special_characters(
    client: TestClient,
    mock_mail_client: Mock,
    create_mock_message: Callable[..., Mock],
    http_status: type,
) -> None:
    """Test messages with special characters in content."""
    # Arrange
    special_message = create_mock_message(
        "special_msg",
        "test@example.com",
        "recipient@example.com",
        "Subject with émojis 🎉 and spëcial chars",
        "2024-01-01T10:00:00Z",
        "Body with special characters: áéíóú, 中文, русский, 🚀",
    )
    mock_mail_client.get_messages.return_value = [special_message]

    # Act
    response = client.get("/messages")

    # Assert
    assert http_status(response.status_code) == http_status.OK  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert len(data) == 1
    assert data[0]["subject"] == "Subject with émojis 🎉 and spëcial chars"
    assert "🚀" in data[0]["body"]


def test_list_messages_with_long_content(
    client: TestClient,
    mock_mail_client: Mock,
    create_mock_message: Callable[..., Mock],
    http_status: type,
) -> None:
    """Test messages with very long content."""
    # Arrange
    LONG_BODY_LEN = 10_000  # noqa: N806
    long_body = "A" * LONG_BODY_LEN
    long_message = create_mock_message(
        "long_msg",
        "test@example.com",
        "recipient@example.com",
        "Long message",
        "2024-01-01T10:00:00Z",
        long_body,
    )
    mock_mail_client.get_messages.return_value = [long_message]

    # Act
    response = client.get("/messages")

    # Assert
    assert http_status(response.status_code) == http_status.OK  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert len(data) == 1
    assert len(data[0]["body"]) == LONG_BODY_LEN


def test_get_message_success(
    client: TestClient,
    mock_mail_client: Mock,
    create_mock_message: Callable[..., Mock],
    http_status: type,
) -> None:
    """Test successful retrieval of a single message."""
    # Arrange
    test_message = create_mock_message(
        "test_msg_001",
        "sender@example.com",
        "recipient@example.com",
        "Test Message",
        "2024-01-01T10:00:00Z",
        "This is a test message body.",
    )
    mock_mail_client.get_message.return_value = test_message

    # Act
    response = client.get("/messages/test_msg_001")

    # Assert
    assert http_status(response.status_code) == http_status.OK  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["id"] == "test_msg_001"
    assert data["from"] == "sender@example.com"
    assert data["to"] == "recipient@example.com"
    assert data["subject"] == "Test Message"
    assert data["date"] == "2024-01-01T10:00:00Z"
    assert data["body"] == "This is a test message body."

    # Verify the mock was called correctly
    mock_mail_client.get_message.assert_called_with("test_msg_001")


def test_get_message_not_found(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test when a message is not found."""
    # Arrange
    mock_mail_client.get_message.side_effect = Exception("Message not found")

    # Act
    response = client.get("/messages/nonexistent_msg")

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == "Message not found"

    # Verify the mock was called correctly
    mock_mail_client.get_message.assert_called_with("nonexistent_msg")


def test_get_message_client_exception(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test when the mail client raises an exception while getting a message."""
    # Arrange
    mock_mail_client.get_message.side_effect = RuntimeError(
        "Failed to connect to mail server",
    )

    # Act
    response = client.get("/messages/some_msg_id")

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == "Failed to connect to mail server"
