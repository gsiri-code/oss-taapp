"""Tests for ServiceMessage class."""

import pytest
from mail_client_adapter.service_message import ServiceMessage


class TestServiceMessage:
    """Test cases for ServiceMessage class."""

    def test_service_message_initialization(self) -> None:
        """Test ServiceMessage initialization with complete data."""
        message_data = {
            "id": "msg123",
            "from": "sender@example.com",
            "to": "recipient@example.com",
            "date": "2024-01-01T00:00:00Z",
            "subject": "Test Subject",
            "body": "Test Body Content",
        }

        message = ServiceMessage(message_data)

        assert message.id == "msg123"
        assert message.from_ == "sender@example.com"
        assert message.to == "recipient@example.com"
        assert message.date == "2024-01-01T00:00:00Z"
        assert message.subject == "Test Subject"
        assert message.body == "Test Body Content"

    def test_service_message_with_missing_fields(self) -> None:
        """Test ServiceMessage with missing fields returns empty strings."""
        message_data = {
            "id": "msg123",
            "subject": "Test Subject",
            # Missing from, to, date, body
        }

        message = ServiceMessage(message_data)

        assert message.id == "msg123"
        assert message.from_ == ""
        assert message.to == ""
        assert message.date == ""
        assert message.subject == "Test Subject"
        assert message.body == ""

    def test_service_message_with_empty_data(self) -> None:
        """Test ServiceMessage with empty data dictionary."""
        message_data: dict[str, str] = {}

        message = ServiceMessage(message_data)

        assert message.id == ""
        assert message.from_ == ""
        assert message.to == ""
        assert message.date == ""
        assert message.subject == ""
        assert message.body == ""

    def test_service_message_with_none_values(self) -> None:
        """Test ServiceMessage with None values in data."""
        message_data = {
            "id": "msg123",
            "from": None,
            "to": "recipient@example.com",
            "date": "2024-01-01T00:00:00Z",
            "subject": None,
            "body": "Test Body",
        }

        message = ServiceMessage(message_data)  # type: ignore[arg-type] # purpose of the test

        assert message.id == "msg123"
        assert message.from_ is None  # None values are preserved
        assert message.to == "recipient@example.com"
        assert message.date == "2024-01-01T00:00:00Z"
        assert message.subject is None  # None values are preserved
        assert message.body == "Test Body"

    def test_service_message_with_extra_fields(self) -> None:
        """Test ServiceMessage with extra fields in data."""
        message_data = {
            "id": "msg123",
            "from": "sender@example.com",
            "to": "recipient@example.com",
            "date": "2024-01-01T00:00:00Z",
            "subject": "Test Subject",
            "body": "Test Body",
            "extra_field": "extra_value",
            "another_field": "123",
        }

        message = ServiceMessage(message_data)

        # Should still work with extra fields
        assert message.id == "msg123"
        assert message.from_ == "sender@example.com"
        assert message.to == "recipient@example.com"
        assert message.date == "2024-01-01T00:00:00Z"
        assert message.subject == "Test Subject"
        assert message.body == "Test Body"

    def test_service_message_properties_are_readonly(self) -> None:
        """Test that ServiceMessage properties are read-only."""
        message_data = {"id": "msg123", "from": "sender@example.com", "subject": "Test Subject"}

        message = ServiceMessage(message_data)

        # Properties should be read-only (no setters)
        with pytest.raises(AttributeError):
            message.id = "new_id"  # type: ignore[misc] # purpose of the test

        with pytest.raises(AttributeError):
            message.from_ = "new_sender@example.com"  # type: ignore[misc] # purpose of the test

        with pytest.raises(AttributeError):
            message.subject = "New Subject"  # type: ignore[misc] # purpose of the test

    def test_service_message_with_special_characters(self) -> None:
        """Test ServiceMessage with special characters in data."""
        message_data = {
            "id": "msg-123_456",
            "from": "sender+tag@example.com",
            "to": "recipient@example.co.uk",
            "date": "2024-01-01T12:30:45.123Z",
            "subject": "Test Subject with émojis 🎉 and spëcial chars",
            "body": "Body with\nnewlines\tand\ttabs",
        }

        message = ServiceMessage(message_data)

        assert message.id == "msg-123_456"
        assert message.from_ == "sender+tag@example.com"
        assert message.to == "recipient@example.co.uk"
        assert message.date == "2024-01-01T12:30:45.123Z"
        assert message.subject == "Test Subject with émojis 🎉 and spëcial chars"
        assert message.body == "Body with\nnewlines\tand\ttabs"

    def test_service_message_inheritance(self) -> None:
        """Test that ServiceMessage inherits from Message."""
        from mail_client_api.message import Message

        message_data = {"id": "msg123", "subject": "Test"}
        message = ServiceMessage(message_data)

        assert isinstance(message, Message)

    def test_service_message_data_storage(self) -> None:
        """Test that ServiceMessage stores data internally."""
        message_data = {"id": "msg123", "from": "sender@example.com", "subject": "Test Subject"}

        message = ServiceMessage(message_data)

        # Access the internal _data attribute
        assert hasattr(message, "_data")
        assert message._data == message_data

    def test_service_message_with_unicode(self) -> None:
        """Test ServiceMessage with Unicode characters."""
        message_data = {
            "id": "msg123",
            "from": "发送者@example.com",
            "to": "收件人@example.com",
            "date": "2024-01-01T00:00:00Z",
            "subject": "测试主题",
            "body": "这是测试内容",
        }

        message = ServiceMessage(message_data)

        assert message.id == "msg123"
        assert message.from_ == "发送者@example.com"
        assert message.to == "收件人@example.com"
        assert message.date == "2024-01-01T00:00:00Z"
        assert message.subject == "测试主题"
        assert message.body == "这是测试内容"
