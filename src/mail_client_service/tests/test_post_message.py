"""Unit tests for POST endpoints in the mail client service."""

from unittest.mock import Mock

from fastapi.testclient import TestClient


def test_mark_message_as_read_success(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test successfully marking a message as read."""
    # Arrange
    message_id = "test_msg_001"
    mock_mail_client.mark_as_read.return_value = True

    # Act
    response = client.post(f"/messages/{message_id}/mark-as-read")

    # Assert
    assert http_status(response.status_code) == http_status.OK  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == f"Message {message_id} marked as read."

    # Verify the mock was called correctly
    mock_mail_client.mark_as_read.assert_called_once_with(message_id)


def test_mark_message_as_read_client_exception(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test when the mail client raises an exception during mark as read."""
    # Arrange
    message_id = "test_msg_002"
    mock_mail_client.mark_as_read.side_effect = RuntimeError("Failed to mark as read")

    # Act
    response = client.post(f"/messages/{message_id}/mark-as-read")

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == "Failed to mark as read"

    # Verify the mock was called correctly
    mock_mail_client.mark_as_read.assert_called_once_with(message_id)


def test_mark_message_as_read_nonexistent_message(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test marking a nonexistent message as read."""
    # Arrange
    message_id = "nonexistent_msg"
    mock_mail_client.mark_as_read.side_effect = Exception("Message not found")

    # Act
    response = client.post(f"/messages/{message_id}/mark-as-read")

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == "Message not found"

    # Verify the mock was called correctly
    mock_mail_client.mark_as_read.assert_called_once_with(message_id)


def test_mark_message_as_read_empty_message_id(
    client: TestClient,
    http_status: type,
) -> None:
    """Test marking a message as read with empty message ID."""
    # Arrange
    message_id = ""

    # Act - empty message_id should result in 404 due to path parameter validation
    response = client.post(f"/messages/{message_id}/mark-as-read")

    # Assert
    assert http_status(response.status_code) == http_status.NOT_FOUND  # type: ignore[attr-defined]  # pytest fixture


def test_mark_message_as_read_with_special_characters(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test marking a message as read with special characters in message ID."""
    # Arrange
    message_id = "msg_with_émoji_🎉"
    mock_mail_client.mark_as_read.return_value = True

    # Act
    response = client.post(f"/messages/{message_id}/mark-as-read")

    # Assert
    assert http_status(response.status_code) == http_status.OK  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == f"Message {message_id} marked as read."

    # Verify the mock was called correctly
    mock_mail_client.mark_as_read.assert_called_once_with(message_id)


def test_mark_message_as_read_very_long_message_id(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test marking a message as read with very long message ID."""
    # Arrange
    message_id = "a" * 1000  # Very long message ID
    mock_mail_client.mark_as_read.return_value = True

    # Act
    response = client.post(f"/messages/{message_id}/mark-as-read")

    # Assert
    assert http_status(response.status_code) == http_status.OK  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == f"Message {message_id} marked as read."

    # Verify the mock was called correctly
    mock_mail_client.mark_as_read.assert_called_once_with(message_id)


def test_mark_message_as_read_authentication_error(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test marking a message as read when authentication fails."""
    # Arrange
    message_id = "test_msg_003"
    mock_mail_client.mark_as_read.side_effect = Exception("Authentication failed")

    # Act
    response = client.post(f"/messages/{message_id}/mark-as-read")

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == "Authentication failed"

    # Verify the mock was called correctly
    mock_mail_client.mark_as_read.assert_called_once_with(message_id)


def test_mark_message_as_read_network_error(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test marking a message as read when network error occurs."""
    # Arrange
    message_id = "test_msg_004"
    mock_mail_client.mark_as_read.side_effect = ConnectionError("Network connection failed")

    # Act
    response = client.post(f"/messages/{message_id}/mark-as-read")

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == "Network connection failed"

    # Verify the mock was called correctly
    mock_mail_client.mark_as_read.assert_called_once_with(message_id)


def test_mark_message_as_read_value_error(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test marking a message as read when ValueError is raised."""
    # Arrange
    message_id = "test_msg_005"
    mock_mail_client.mark_as_read.side_effect = ValueError("Invalid message ID format")

    # Act
    response = client.post(f"/messages/{message_id}/mark-as-read")

    # Assert
    assert http_status(response.status_code) == http_status.INTERNAL_SERVER_ERROR  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == "Invalid message ID format"

    # Verify the mock was called correctly
    mock_mail_client.mark_as_read.assert_called_once_with(message_id)


def test_mark_message_as_read_with_url_encoded_characters(
    client: TestClient,
    mock_mail_client: Mock,
    http_status: type,
) -> None:
    """Test marking a message as read with URL-encoded characters in message ID."""
    # Arrange
    message_id = "msg@example.com"  # Contains @ which might be URL encoded
    mock_mail_client.mark_as_read.return_value = True

    # Act
    response = client.post(f"/messages/{message_id}/mark-as-read")

    # Assert
    assert http_status(response.status_code) == http_status.OK  # type: ignore[attr-defined]  # pytest fixture
    data = response.json()
    assert data["detail"] == f"Message {message_id} marked as read."

    # Verify the mock was called correctly
    mock_mail_client.mark_as_read.assert_called_once_with(message_id)
