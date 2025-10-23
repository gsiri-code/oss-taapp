"""Unit tests for mail client service API endpoints."""

from collections.abc import Callable
from unittest.mock import Mock

from fastapi.testclient import TestClient


def test_get_message_with_special_characters(
    client: TestClient,
    mock_mail_client: Mock,
    create_mock_message: Callable[..., Mock],
    http_status: type,
) -> None:
    """Test retrieving a message with special characters."""
    special_message = create_mock_message(
        "special_msg",
        "test@example.com",
        "recipient@example.com",
        "Subject with émojis 🎉 and spëcial chars",
        "2024-01-01T10:00:00Z",
        "Body with special characters: áéíóú, 中文, русский, 🚀",
    )
    mock_mail_client.get_message.return_value = special_message
    response = client.get("/messages/special_msg")
    assert http_status(response.status_code) == http_status.OK  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["subject"] == "Subject with émojis 🎉 and spëcial chars"
    assert "🚀" in data["body"]


def test_get_message_with_long_content(
    client: TestClient,
    mock_mail_client: Mock,
    create_mock_message: Callable[..., Mock],
    http_status: type,
) -> None:
    """Test retrieving a message with very long content."""
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
    mock_mail_client.get_message.return_value = long_message
    response = client.get("/messages/long_msg")
    assert http_status(response.status_code) == http_status.OK  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["id"] == "long_msg"
    assert len(data["body"]) == LONG_BODY_LEN


def test_get_message_client_exception_message(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test when the mail client raises an exception message."""
    mock_mail_client.get_message.side_effect = Exception("Mail client connection failed")
    response = client.get("/messages/any_id")
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert "detail" in data
    assert "Mail client connection failed" in data["detail"]


def test_get_message_client_runtime_error(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test when the mail client raises a RuntimeError."""
    mock_mail_client.get_message.side_effect = RuntimeError("Authentication failed")
    response = client.get("/messages/any_id")
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == "Authentication failed"


def test_get_message_client_value_error(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test when the mail client raises a ValueError."""
    mock_mail_client.get_message.side_effect = ValueError("Invalid configuration")
    response = client.get("/messages/any_id")
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == "Invalid configuration"


def test_get_message_single_message(
    client: TestClient,
    mock_mail_client: Mock,
    create_mock_message: Callable[..., Mock],
    http_status: type,
) -> None:
    """Test retrieving a single message."""
    single_message = create_mock_message(
        "single_msg",
        "single@example.com",
        "recipient@example.com",
        "Single Message",
        "2024-01-01T10:00:00Z",
        "Single message body.",
    )
    mock_mail_client.get_message.return_value = single_message
    response = client.get("/messages/single_msg")
    assert http_status(response.status_code) == http_status.OK  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["id"] == "single_msg"
    assert data["from"] == "single@example.com"
