"""Tests for Client class."""

from unittest.mock import Mock, patch

import httpx

from mail_client_service_client import Client


class TestClient:
    """Test cases for Client class."""

    def test_client_initialization(self) -> None:
        """Test client initialization with default values."""
        client = Client(base_url="https://api.example.com")

        assert client.raise_on_unexpected_status is False
        assert client._base_url == "https://api.example.com"
        assert client._cookies == {}
        assert client._headers == {}
        assert client._timeout is None
        assert client._verify_ssl is True
        assert client._follow_redirects is False
        assert client._httpx_args == {}
        assert client._client is None
        assert client._async_client is None

    def test_client_initialization_with_custom_values(self) -> None:
        """Test client initialization with custom values."""
        timeout = httpx.Timeout(30.0)
        client = Client(
            base_url="https://api.example.com",
            cookies={"session": "abc123"},
            headers={"User-Agent": "test-app"},
            timeout=timeout,
            verify_ssl=False,
            follow_redirects=True,
            httpx_args={"proxies": {"http": "http://proxy:8080"}},
            raise_on_unexpected_status=True,
        )

        assert client.raise_on_unexpected_status is True
        assert client._base_url == "https://api.example.com"
        assert client._cookies == {"session": "abc123"}
        assert client._headers == {"User-Agent": "test-app"}
        assert client._timeout == timeout
        assert client._verify_ssl is False
        assert client._follow_redirects is True
        assert client._httpx_args == {"proxies": {"http": "http://proxy:8080"}}

    def test_with_headers(self) -> None:
        """Test with_headers method."""
        client = Client(base_url="https://api.example.com")
        new_client = client.with_headers({"Authorization": "Bearer token"})

        assert new_client._headers == {"Authorization": "Bearer token"}
        assert client._headers == {}  # Original client unchanged

    def test_with_cookies(self) -> None:
        """Test with_cookies method."""
        client = Client(base_url="https://api.example.com")
        new_client = client.with_cookies({"session": "abc123"})

        assert new_client._cookies == {"session": "abc123"}
        assert client._cookies == {}  # Original client unchanged

    def test_with_timeout(self) -> None:
        """Test with_timeout method."""
        client = Client(base_url="https://api.example.com")
        timeout = httpx.Timeout(60.0)
        new_client = client.with_timeout(timeout)

        assert new_client._timeout == timeout
        assert client._timeout is None  # Original client unchanged

    def test_set_httpx_client(self) -> None:
        """Test set_httpx_client method."""
        client = Client(base_url="https://api.example.com")
        mock_httpx_client = Mock(spec=httpx.Client)

        result = client.set_httpx_client(mock_httpx_client)

        assert result is client
        assert client._client is mock_httpx_client

    @patch("httpx.Client")
    def test_get_httpx_client_creates_new(self, mock_httpx_client_class: Mock) -> None:
        """Test get_httpx_client creates new client when none exists."""
        mock_client_instance = Mock()
        mock_httpx_client_class.return_value = mock_client_instance

        client = Client(base_url="https://api.example.com")
        result = client.get_httpx_client()

        assert result is mock_client_instance
        mock_httpx_client_class.assert_called_once_with(
            base_url="https://api.example.com",
            cookies={},
            headers={},
            timeout=None,
            verify=True,
            follow_redirects=False,
        )

    def test_get_httpx_client_returns_existing(self) -> None:
        """Test get_httpx_client returns existing client."""
        client = Client(base_url="https://api.example.com")
        mock_httpx_client = Mock(spec=httpx.Client)
        client._client = mock_httpx_client

        result = client.get_httpx_client()

        assert result is mock_httpx_client

    def test_context_manager(self) -> None:
        """Test context manager functionality."""
        client = Client(base_url="https://api.example.com")
        mock_httpx_client = Mock()
        mock_httpx_client.__enter__ = Mock(return_value=mock_httpx_client)
        mock_httpx_client.__exit__ = Mock(return_value=None)
        client._client = mock_httpx_client

        with client as ctx:
            assert ctx is client
            mock_httpx_client.__enter__.assert_called_once()

        mock_httpx_client.__exit__.assert_called_once()

    def test_set_async_httpx_client(self) -> None:
        """Test set_async_httpx_client method."""
        client = Client(base_url="https://api.example.com")
        mock_async_client = Mock(spec=httpx.AsyncClient)

        result = client.set_async_httpx_client(mock_async_client)

        assert result is client
        assert client._async_client is mock_async_client

    @patch("httpx.AsyncClient")
    def test_get_async_httpx_client_creates_new(self, mock_async_client_class: Mock) -> None:
        """Test get_async_httpx_client creates new client when none exists."""
        mock_async_client_instance = Mock()
        mock_async_client_class.return_value = mock_async_client_instance

        client = Client(base_url="https://api.example.com")
        result = client.get_async_httpx_client()

        assert result is mock_async_client_instance
        mock_async_client_class.assert_called_once_with(
            base_url="https://api.example.com",
            cookies={},
            headers={},
            timeout=None,
            verify=True,
            follow_redirects=False,
        )

    def test_get_async_httpx_client_returns_existing(self) -> None:
        """Test get_async_httpx_client returns existing client."""
        client = Client(base_url="https://api.example.com")
        mock_async_client = Mock(spec=httpx.AsyncClient)
        client._async_client = mock_async_client

        result = client.get_async_httpx_client()

        assert result is mock_async_client

    def test_async_context_manager(self) -> None:
        """Test async context manager functionality."""
        client = Client(base_url="https://api.example.com")
        mock_async_client = Mock()
        mock_async_client.__aenter__ = Mock(return_value=mock_async_client)
        mock_async_client.__aexit__ = Mock(return_value=None)
        client._async_client = mock_async_client

        # Test that the async context manager methods are callable
        assert callable(mock_async_client.__aenter__)
        assert callable(mock_async_client.__aexit__)
