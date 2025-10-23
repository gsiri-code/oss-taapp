"""Tests for ServiceClientAdapter."""

from unittest.mock import Mock, patch

import pytest

from mail_client_adapter import ServiceClientAdapter
from mail_client_service_client import Client


class TestServiceClientAdapter:
    """Test cases for ServiceClientAdapter."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_service_client = Mock(spec=Client)
        self.adapter = ServiceClientAdapter(self.mock_service_client)

    def test_init(self) -> None:
        """Test adapter initialization."""
        assert self.adapter._service_client is self.mock_service_client

    @patch("mail_client_adapter.service_client_adapter.get_message_sync")
    def test_get_message_success(self, mock_get_message: Mock) -> None:
        """Test successful message retrieval."""
        # Mock response
        mock_response = {
            "id": "msg123",
            "from": "sender@example.com",
            "to": "recipient@example.com",
            "date": "2024-01-01T00:00:00Z",
            "subject": "Test Subject",
            "body": "Test Body",
        }
        mock_get_message.return_value = mock_response

        # Call the method
        message = self.adapter.get_message("msg123")

        # Verify the response
        assert message.id == "msg123"
        assert message.from_ == "sender@example.com"
        assert message.to == "recipient@example.com"
        assert message.date == "2024-01-01T00:00:00Z"
        assert message.subject == "Test Subject"
        assert message.body == "Test Body"

        # Verify the service client was called correctly
        mock_get_message.assert_called_once_with(message_id="msg123", client=self.mock_service_client)

    @patch("mail_client_adapter.service_client_adapter.get_message_sync")
    def test_get_message_not_found(self, mock_get_message: Mock) -> None:
        """Test message not found scenario."""
        mock_get_message.return_value = None

        with pytest.raises(RuntimeError, match="Message with ID msg123 not found"):
            self.adapter.get_message("msg123")

    @patch("mail_client_adapter.service_client_adapter.get_message_sync")
    def test_get_message_exception(self, mock_get_message: Mock) -> None:
        """Test exception handling in get_message."""
        mock_get_message.side_effect = Exception("Network error")

        with pytest.raises(RuntimeError, match="Failed to get message msg123"):
            self.adapter.get_message("msg123")

    @patch("mail_client_adapter.service_client_adapter.delete_message_sync")
    def test_delete_message_success(self, mock_delete_message: Mock) -> None:
        """Test successful message deletion."""
        mock_response = {"success": True}
        mock_delete_message.return_value = mock_response

        result = self.adapter.delete_message("msg123")

        assert result is True
        mock_delete_message.assert_called_once_with(message_id="msg123", client=self.mock_service_client)

    @patch("mail_client_adapter.service_client_adapter.delete_message_sync")
    def test_delete_message_failure(self, mock_delete_message: Mock) -> None:
        """Test message deletion failure."""
        mock_delete_message.return_value = None

        result = self.adapter.delete_message("msg123")

        assert result is False

    @patch("mail_client_adapter.service_client_adapter.delete_message_sync")
    def test_delete_message_exception(self, mock_delete_message: Mock) -> None:
        """Test exception handling in delete_message."""
        mock_delete_message.side_effect = Exception("Network error")

        result = self.adapter.delete_message("msg123")

        assert result is False

    @patch("mail_client_adapter.service_client_adapter.mark_as_read_sync")
    def test_mark_as_read_success(self, mock_mark_as_read: Mock) -> None:
        """Test successful mark as read."""
        mock_response = {"success": True}
        mock_mark_as_read.return_value = mock_response

        result = self.adapter.mark_as_read("msg123")

        assert result is True
        mock_mark_as_read.assert_called_once_with(message_id="msg123", client=self.mock_service_client)

    @patch("mail_client_adapter.service_client_adapter.mark_as_read_sync")
    def test_mark_as_read_failure(self, mock_mark_as_read: Mock) -> None:
        """Test mark as read failure."""
        mock_mark_as_read.return_value = None

        result = self.adapter.mark_as_read("msg123")

        assert result is False

    @patch("mail_client_adapter.service_client_adapter.mark_as_read_sync")
    def test_mark_as_read_exception(self, mock_mark_as_read: Mock) -> None:
        """Test exception handling in mark_as_read."""
        mock_mark_as_read.side_effect = Exception("Network error")

        result = self.adapter.mark_as_read("msg123")

        assert result is False

    @patch("mail_client_adapter.service_client_adapter.list_messages_sync")
    def test_get_messages_success(self, mock_list_messages: Mock) -> None:
        """Test successful message listing."""
        # Mock response with multiple messages
        mock_response = [
            {
                "id": "msg1",
                "from": "sender1@example.com",
                "to": "recipient@example.com",
                "date": "2024-01-01T00:00:00Z",
                "subject": "Subject 1",
                "body": "Body 1",
            },
            {
                "id": "msg2",
                "from": "sender2@example.com",
                "to": "recipient@example.com",
                "date": "2024-01-02T00:00:00Z",
                "subject": "Subject 2",
                "body": "Body 2",
            },
        ]

        mock_list_messages.return_value = mock_response

        # Call the method
        messages = list(self.adapter.get_messages(max_results=10))

        # Verify the response
        assert len(messages) == len(mock_response)
        assert messages[0].id == "msg1"
        assert messages[0].subject == "Subject 1"
        assert messages[1].id == "msg2"
        assert messages[1].subject == "Subject 2"

        mock_list_messages.assert_called_once_with(client=self.mock_service_client)

    @patch("mail_client_adapter.service_client_adapter.list_messages_sync")
    def test_get_messages_with_limit(self, mock_list_messages: Mock) -> None:
        """Test message listing with max_results limit."""
        # Mock response with more messages than the limit
        mock_messages = []
        for i in range(5):
            mock_msg = {
                "id": f"msg{i}",
                "from": f"sender{i}@example.com",
                "to": "recipient@example.com",
                "date": f"2024-01-0{i + 1}T00:00:00Z",
                "subject": f"Subject {i}",
                "body": f"Body {i}",
            }
            mock_messages.append(mock_msg)

        mock_list_messages.return_value = mock_messages

        # Call with limit
        limited_message_count = 3
        messages = list(self.adapter.get_messages(max_results=limited_message_count))

        # Verify only 3 messages were returned
        assert len(messages) == limited_message_count

    @patch("mail_client_adapter.service_client_adapter.list_messages_sync")
    def test_get_messages_empty(self, mock_list_messages: Mock) -> None:
        """Test message listing when no messages are returned."""
        mock_list_messages.return_value = []

        messages = list(self.adapter.get_messages())

        assert len(messages) == 0

    @patch("mail_client_adapter.service_client_adapter.list_messages_sync")
    def test_get_messages_exception(self, mock_list_messages: Mock) -> None:
        """Test exception handling in get_messages."""
        mock_list_messages.side_effect = Exception("Network error")

        messages = list(self.adapter.get_messages())

        # Should return empty iterator on exception
        assert len(messages) == 0
