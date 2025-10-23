"""Tests for API functions."""

from unittest.mock import Mock

import pytest
from mail_client_adapter.api import (
    delete_message_sync,
    get_message_sync,
    list_messages_sync,
    mark_as_read_sync,
)

from mail_client_service_client import Client


class TestListMessagesSync:
    """Test cases for list_messages_sync function."""

    def test_list_messages_success(self) -> None:
        """Test successful message listing."""
        # Mock client and response
        mock_client = Mock(spec=Client)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "msg1", "from": "sender1@example.com", "subject": "Test 1"},
            {"id": "msg2", "from": "sender2@example.com", "subject": "Test 2"},
        ]
        mock_client.get_httpx_client.return_value.request.return_value = mock_response

        # Call the function
        result = list_messages_sync(client=mock_client)

        # Verify the result
        assert result == [
            {"id": "msg1", "from": "sender1@example.com", "subject": "Test 1"},
            {"id": "msg2", "from": "sender2@example.com", "subject": "Test 2"},
        ]

    def test_list_messages_non_200_status(self) -> None:
        """Test handling of non-200 status code."""
        # Mock client and response
        mock_client = Mock(spec=Client)
        mock_client.raise_on_unexpected_status = False
        mock_response = Mock()
        mock_response.status_code = 404
        mock_client.get_httpx_client.return_value.request.return_value = mock_response

        # Call the function
        result = list_messages_sync(client=mock_client)

        # Verify the result
        assert result is None

    def test_list_messages_non_200_status_with_raise(self) -> None:
        """Test handling of non-200 status code with raise_on_unexpected_status=True."""
        # Mock client and response
        mock_client = Mock(spec=Client)
        mock_client.raise_on_unexpected_status = True
        mock_response = Mock()
        mock_response.status_code = 500
        mock_client.get_httpx_client.return_value.request.return_value = mock_response

        # Call the function and expect exception
        with pytest.raises(Exception, match="Unexpected status code: 500"):
            list_messages_sync(client=mock_client)


class TestGetMessageSync:
    """Test cases for get_message_sync function."""

    def test_get_message_success(self) -> None:
        """Test successful message retrieval."""
        # Mock client and response
        mock_client = Mock(spec=Client)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "msg123",
            "from": "sender@example.com",
            "subject": "Test Subject",
            "body": "Test Body",
        }
        mock_client.get_httpx_client.return_value.request.return_value = mock_response

        # Call the function
        result = get_message_sync(message_id="msg123", client=mock_client)

        # Verify the result
        assert result == {
            "id": "msg123",
            "from": "sender@example.com",
            "subject": "Test Subject",
            "body": "Test Body",
        }

    def test_get_message_not_found(self) -> None:
        """Test message not found scenario."""
        # Mock client and response
        mock_client = Mock(spec=Client)
        mock_client.raise_on_unexpected_status = False
        mock_response = Mock()
        mock_response.status_code = 404
        mock_client.get_httpx_client.return_value.request.return_value = mock_response

        # Call the function
        result = get_message_sync(message_id="msg123", client=mock_client)

        # Verify the result
        assert result is None

    def test_get_message_server_error_with_raise(self) -> None:
        """Test server error with raise_on_unexpected_status=True."""
        # Mock client and response
        mock_client = Mock(spec=Client)
        mock_client.raise_on_unexpected_status = True
        mock_response = Mock()
        mock_response.status_code = 500
        mock_client.get_httpx_client.return_value.request.return_value = mock_response

        # Call the function and expect exception
        with pytest.raises(Exception, match="Unexpected status code: 500"):
            get_message_sync(message_id="msg123", client=mock_client)


class TestDeleteMessageSync:
    """Test cases for delete_message_sync function."""

    def test_delete_message_success(self) -> None:
        """Test successful message deletion."""
        # Mock client and response
        mock_client = Mock(spec=Client)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_client.get_httpx_client.return_value.request.return_value = mock_response

        # Call the function
        result = delete_message_sync(message_id="msg123", client=mock_client)

        # Verify the result
        assert result == {"success": True}

    def test_delete_message_failure(self) -> None:
        """Test message deletion failure."""
        # Mock client and response
        mock_client = Mock(spec=Client)
        mock_client.raise_on_unexpected_status = False
        mock_response = Mock()
        mock_response.status_code = 400
        mock_client.get_httpx_client.return_value.request.return_value = mock_response

        # Call the function
        result = delete_message_sync(message_id="msg123", client=mock_client)

        # Verify the result
        assert result is None


class TestMarkAsReadSync:
    """Test cases for mark_as_read_sync function."""

    def test_mark_as_read_success(self) -> None:
        """Test successful mark as read."""
        # Mock client and response
        mock_client = Mock(spec=Client)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_client.get_httpx_client.return_value.request.return_value = mock_response

        # Call the function
        result = mark_as_read_sync(message_id="msg123", client=mock_client)

        # Verify the result
        assert result == {"success": True}

    def test_mark_as_read_failure(self) -> None:
        """Test mark as read failure."""
        # Mock client and response
        mock_client = Mock(spec=Client)
        mock_client.raise_on_unexpected_status = False
        mock_response = Mock()
        mock_response.status_code = 403
        mock_client.get_httpx_client.return_value.request.return_value = mock_response

        # Call the function
        result = mark_as_read_sync(message_id="msg123", client=mock_client)

        # Verify the result
        assert result is None

    def test_mark_as_read_unauthorized_with_raise(self) -> None:
        """Test unauthorized with raise_on_unexpected_status=True."""
        # Mock client and response
        mock_client = Mock(spec=Client)
        mock_client.raise_on_unexpected_status = True
        mock_response = Mock()
        mock_response.status_code = 401
        mock_client.get_httpx_client.return_value.request.return_value = mock_response

        # Call the function and expect exception
        with pytest.raises(Exception, match="Unexpected status code: 401"):
            mark_as_read_sync(message_id="msg123", client=mock_client)
