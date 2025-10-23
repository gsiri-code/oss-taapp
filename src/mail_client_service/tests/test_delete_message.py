"""Unit tests for mail client service delete message endpoint."""

from unittest.mock import Mock

from fastapi.testclient import TestClient


def test_delete_message_success(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test successful deletion of a message."""
    # Act
    response = client.delete("/messages/test_msg_001")

    # Assert
    assert http_status(response.status_code) == http_status.OK  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == "Message test_msg_001 deleted."

    # Verify the mock was called correctly
    mock_mail_client.delete_message.assert_called_once_with("test_msg_001")


def test_delete_message_client_exception(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test when the mail client raises an exception during deletion."""
    # Arrange
    mock_mail_client.delete_message.side_effect = Exception("Failed to delete message")

    # Act
    response = client.delete("/messages/error_msg")

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == "Failed to delete message"

    # Verify the mock was called correctly
    mock_mail_client.delete_message.assert_called_once_with("error_msg")


def test_delete_message_not_found(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test deleting a non-existent message."""
    # Arrange
    mock_mail_client.delete_message.side_effect = Exception("Message not found")

    # Act
    response = client.delete("/messages/nonexistent_msg")

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == "Message not found"

    # Verify the mock was called correctly
    mock_mail_client.delete_message.assert_called_once_with("nonexistent_msg")


def test_delete_message_runtime_error(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test when the mail client raises a RuntimeError during deletion."""
    # Arrange
    mock_mail_client.delete_message.side_effect = RuntimeError("Authentication failed")

    # Act
    response = client.delete("/messages/auth_error_msg")

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == "Authentication failed"

    # Verify the mock was called correctly
    mock_mail_client.delete_message.assert_called_once_with("auth_error_msg")


def test_delete_message_value_error(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test when the mail client raises a ValueError during deletion."""
    # Arrange
    mock_mail_client.delete_message.side_effect = ValueError("Invalid message ID format")

    # Act
    response = client.delete("/messages/invalid_id")

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == "Invalid message ID format"

    # Verify the mock was called correctly
    mock_mail_client.delete_message.assert_called_once_with("invalid_id")


def test_delete_message_with_special_characters(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test deleting a message with special characters in ID."""
    # Arrange
    special_id = "msg_with_émojis_🎉_and_spëcial_chars"

    # Act
    response = client.delete(f"/messages/{special_id}")

    # Assert
    assert http_status(response.status_code) == http_status.OK  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == f"Message {special_id} deleted."

    # Verify the mock was called correctly
    mock_mail_client.delete_message.assert_called_once_with(special_id)
