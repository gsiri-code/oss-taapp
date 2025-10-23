"""Edge case tests for ServiceClientAdapter."""

from unittest.mock import Mock, patch

import pytest

from mail_client_adapter import ServiceClientAdapter
from mail_client_service_client import Client


class TestServiceClientAdapterEdgeCases:
    """Edge case test cases for ServiceClientAdapter."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_service_client = Mock(spec=Client)
        self.adapter = ServiceClientAdapter(self.mock_service_client)

    def test_init_with_none_client(self) -> None:
        """Test adapter initialization with None client."""
        # The adapter doesn't validate the client parameter, so this should work
        adapter = ServiceClientAdapter(None)  # type: ignore[arg-type] # purpose of the test
        assert adapter._service_client is None

    def test_get_message_with_empty_id(self) -> None:
        """Test get_message with empty message ID."""
        with patch("mail_client_adapter.service_client_adapter.get_message_sync") as mock_get_message:
            mock_get_message.return_value = None

            with pytest.raises(RuntimeError, match="Message with ID  not found"):
                self.adapter.get_message("")

    def test_get_message_with_none_id(self) -> None:
        """Test get_message with None message ID."""
        with patch("mail_client_adapter.service_client_adapter.get_message_sync") as mock_get_message:
            mock_get_message.return_value = None

            with pytest.raises(RuntimeError, match="Message with ID None not found"):
                self.adapter.get_message(None)  # type: ignore[arg-type] # purpose of the test

    def test_get_message_with_very_long_id(self) -> None:
        """Test get_message with very long message ID."""
        long_id = "a" * 1000

        with patch("mail_client_adapter.service_client_adapter.get_message_sync") as mock_get_message:
            mock_response = {"id": long_id, "from": "sender@example.com", "subject": "Test", "body": "Test body"}
            mock_get_message.return_value = mock_response

            message = self.adapter.get_message(long_id)
            assert message.id == long_id

    def test_get_message_with_special_characters_id(self) -> None:
        """Test get_message with special characters in message ID."""
        special_id = "msg-123_456.789+test@special"

        with patch("mail_client_adapter.service_client_adapter.get_message_sync") as mock_get_message:
            mock_response = {"id": special_id, "from": "sender@example.com", "subject": "Test", "body": "Test body"}
            mock_get_message.return_value = mock_response

            message = self.adapter.get_message(special_id)
            assert message.id == special_id

    def test_delete_message_with_empty_id(self) -> None:
        """Test delete_message with empty message ID."""
        with patch("mail_client_adapter.service_client_adapter.delete_message_sync") as mock_delete_message:
            mock_delete_message.return_value = {"success": True}

            result = self.adapter.delete_message("")
            assert result is True

    def test_delete_message_with_none_id(self) -> None:
        """Test delete_message with None message ID."""
        with patch("mail_client_adapter.service_client_adapter.delete_message_sync") as mock_delete_message:
            mock_delete_message.return_value = {"success": True}

            result = self.adapter.delete_message(None)  # type: ignore[arg-type] # purpose of the test
            assert result is True

    def test_mark_as_read_with_empty_id(self) -> None:
        """Test mark_as_read with empty message ID."""
        with patch("mail_client_adapter.service_client_adapter.mark_as_read_sync") as mock_mark_as_read:
            mock_mark_as_read.return_value = {"success": True}

            result = self.adapter.mark_as_read("")
            assert result is True

    def test_mark_as_read_with_none_id(self) -> None:
        """Test mark_as_read with None message ID."""
        with patch("mail_client_adapter.service_client_adapter.mark_as_read_sync") as mock_mark_as_read:
            mock_mark_as_read.return_value = {"success": True}

            result = self.adapter.mark_as_read(None)  # type: ignore[arg-type] # purpose of the test
            assert result is True

    def test_get_messages_with_zero_max_results(self) -> None:
        """Test get_messages with zero max_results."""
        with patch("mail_client_adapter.service_client_adapter.list_messages_sync") as mock_list_messages:
            mock_messages = [
                {"id": "msg1", "from": "sender1@example.com", "subject": "Test 1"},
                {"id": "msg2", "from": "sender2@example.com", "subject": "Test 2"},
            ]
            mock_list_messages.return_value = mock_messages

            # When max_results=0, it should return all messages (not 0)
            messages = list(self.adapter.get_messages(max_results=0))
            assert len(messages) == len(mock_messages)

    def test_get_messages_with_negative_max_results(self) -> None:
        """Test get_messages with negative max_results."""
        with patch("mail_client_adapter.service_client_adapter.list_messages_sync") as mock_list_messages:
            mock_messages = [
                {"id": "msg1", "from": "sender1@example.com", "subject": "Test 1"},
                {"id": "msg2", "from": "sender2@example.com", "subject": "Test 2"},
            ]
            mock_list_messages.return_value = mock_messages

            # When max_results is negative, it should return all messages
            messages = list(self.adapter.get_messages(max_results=-5))
            assert len(messages) == len(mock_messages)

    def test_get_messages_with_very_large_max_results(self) -> None:
        """Test get_messages with very large max_results."""
        NUM_OF_MESSAGES = 5  # noqa: N806
        with patch("mail_client_adapter.service_client_adapter.list_messages_sync") as mock_list_messages:
            mock_messages = [
                {"id": f"msg{i}", "from": f"sender{i}@example.com", "subject": f"Test {i}"} for i in range(NUM_OF_MESSAGES)
            ]
            mock_list_messages.return_value = mock_messages

            messages = list(self.adapter.get_messages(max_results=1000))
            assert len(messages) == NUM_OF_MESSAGES

    def test_get_messages_with_none_max_results(self) -> None:
        """Test get_messages with None max_results."""
        with patch("mail_client_adapter.service_client_adapter.list_messages_sync") as mock_list_messages:
            mock_messages = [{"id": "msg1", "from": "sender1@example.com", "subject": "Test 1"}]
            mock_list_messages.return_value = mock_messages

            # When max_results is None, the condition max_results > 0 is False
            # So it returns all messages (not limited)
            messages = list(self.adapter.get_messages(max_results=None))  # type: ignore[arg-type] # purpose of the test
            assert len(messages) == 1

    def test_get_message_with_malformed_response(self) -> None:
        """Test get_message with malformed response data."""
        with patch("mail_client_adapter.service_client_adapter.get_message_sync") as mock_get_message:
            # Response missing required fields
            mock_response = {"id": "msg123"}  # Missing other fields
            mock_get_message.return_value = mock_response

            message = self.adapter.get_message("msg123")
            assert message.id == "msg123"
            assert message.from_ == ""  # Should default to empty string
            assert message.subject == ""

    def test_delete_message_with_invalid_response(self) -> None:
        """Test delete_message with invalid response."""
        with patch("mail_client_adapter.service_client_adapter.delete_message_sync") as mock_delete_message:
            # Response is not a dictionary
            mock_delete_message.return_value = "invalid_response"

            result = self.adapter.delete_message("msg123")
            assert result is False

    def test_mark_as_read_with_invalid_response(self) -> None:
        """Test mark_as_read with invalid response."""
        with patch("mail_client_adapter.service_client_adapter.mark_as_read_sync") as mock_mark_as_read:
            # Response is not a dictionary
            mock_mark_as_read.return_value = "invalid_response"

            result = self.adapter.mark_as_read("msg123")
            assert result is False

    def test_get_messages_with_invalid_response_type(self) -> None:
        """Test get_messages with invalid response type."""
        with patch("mail_client_adapter.service_client_adapter.list_messages_sync") as mock_list_messages:
            # Response is not a list
            mock_list_messages.return_value = "invalid_response"

            # This should cause an exception when trying to slice a string
            # and return empty iterator
            messages = list(self.adapter.get_messages())
            assert len(messages) == 0

    def test_get_messages_with_empty_strings_in_data(self) -> None:
        """Test get_messages with empty strings in message data."""
        with patch("mail_client_adapter.service_client_adapter.list_messages_sync") as mock_list_messages:
            mock_response = [{"id": "", "from": "", "to": "", "date": "", "subject": "", "body": ""}]
            mock_list_messages.return_value = mock_response

            messages = list(self.adapter.get_messages())
            assert len(messages) == 1
            message = messages[0]
            assert message.id == ""
            assert message.from_ == ""
            assert message.to == ""
            assert message.date == ""
            assert message.subject == ""
            assert message.body == ""

    def test_get_messages_with_unicode_data(self) -> None:
        """Test get_messages with Unicode characters."""
        with patch("mail_client_adapter.service_client_adapter.list_messages_sync") as mock_list_messages:
            mock_response = [
                {
                    "id": "msg123",
                    "from": "发送者@example.com",
                    "to": "收件人@example.com",
                    "date": "2024-01-01T00:00:00Z",
                    "subject": "测试主题",
                    "body": "这是测试内容",
                },
            ]
            mock_list_messages.return_value = mock_response

            messages = list(self.adapter.get_messages())
            assert len(messages) == 1
            message = messages[0]
            assert message.from_ == "发送者@example.com"
            assert message.to == "收件人@example.com"
            assert message.subject == "测试主题"
            assert message.body == "这是测试内容"

    def test_delete_message_with_false_success(self) -> None:
        """Test delete_message with success=False in response."""
        with patch("mail_client_adapter.service_client_adapter.delete_message_sync") as mock_delete_message:
            mock_delete_message.return_value = {"success": False}

            result = self.adapter.delete_message("msg123")
            assert result is False

    def test_mark_as_read_with_false_success(self) -> None:
        """Test mark_as_read with success=False in response."""
        with patch("mail_client_adapter.service_client_adapter.mark_as_read_sync") as mock_mark_as_read:
            mock_mark_as_read.return_value = {"success": False}

            result = self.adapter.mark_as_read("msg123")
            assert result is False

    def test_delete_message_with_missing_success_field(self) -> None:
        """Test delete_message with missing success field (should default to True)."""
        with patch("mail_client_adapter.service_client_adapter.delete_message_sync") as mock_delete_message:
            mock_delete_message.return_value = {"message": "Deleted"}

            result = self.adapter.delete_message("msg123")
            assert result is True  # Should default to True when success field is missing

    def test_mark_as_read_with_missing_success_field(self) -> None:
        """Test mark_as_read with missing success field (should default to True)."""
        with patch("mail_client_adapter.service_client_adapter.mark_as_read_sync") as mock_mark_as_read:
            mock_mark_as_read.return_value = {"message": "Marked as read"}

            result = self.adapter.mark_as_read("msg123")
            assert result is True  # Should default to True when success field is missing
