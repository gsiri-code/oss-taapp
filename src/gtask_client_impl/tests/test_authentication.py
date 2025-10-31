"""Unit tests for GTaskClient authentication and helper methods.

This module contains unit tests for the authentication flow and helper methods
of the GTaskClient class, mocking all external dependencies.
"""

import os
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

from gtask_client_impl.gtask_impl import GTaskClient


class TestGTaskClientAuthentication:
    """Test cases for GTaskClient authentication logic."""

    @patch("gtask_client_impl.gtask_impl.build")
    def test_init_with_provided_service_skips_auth(self, mock_build: Any) -> None:
        """Test that providing a service skips authentication."""
        # ARRANGE
        mock_service = Mock()

        # ACT
        client = GTaskClient(service=mock_service)

        # ASSERT
        assert client.service is mock_service
        mock_build.assert_not_called()

    @patch("gtask_client_impl.gtask_impl.build")
    @patch("gtask_client_impl.gtask_impl.Credentials")
    @patch("gtask_client_impl.gtask_impl.Request")
    @patch.dict(
        os.environ,
        {
            "TASKS_CLIENT_ID": "test_client_id",
            "TASKS_CLIENT_SECRET": "test_client_secret",
            "TASKS_REFRESH_TOKEN": "test_refresh_token",
        },
    )
    def test_init_with_env_vars_success(
        self,
        mock_request: Any,
        mock_creds_class: Any,
        mock_build: Any,
    ) -> None:
        """Test successful initialization with environment variables."""
        # ARRANGE
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True
        mock_creds.refresh_token = "test_refresh_token"
        mock_creds.to_json.return_value = '{"token": "test"}'  # Mock to_json method
        mock_creds_class.return_value = mock_creds

        mock_service = Mock()
        mock_build.return_value = mock_service

        # ACT
        with (
            patch.object(GTaskClient, "_save_token") as mock_save,
            patch("gtask_client_impl.gtask_impl.Path") as mock_path,
        ):
            # Mock token.json doesn't exist so _save_token will be called
            mock_path.return_value.exists.return_value = False

            client = GTaskClient()

            # ASSERT
            assert client.service is mock_service
            mock_creds_class.assert_called_once_with(
                None,
                refresh_token="test_refresh_token",
                token_uri="https://oauth2.googleapis.com/token",
                client_id="test_client_id",
                client_secret="test_client_secret",
                scopes=GTaskClient.SCOPES,
            )
            mock_creds.refresh.assert_called_once()
            mock_build.assert_called_once_with("tasks", "v1", credentials=mock_creds)
            mock_save.assert_called_once_with(mock_creds, "token.json")

    @patch("gtask_client_impl.gtask_impl.build")
    @patch("gtask_client_impl.gtask_impl.Credentials")
    @patch("gtask_client_impl.gtask_impl.Request")
    @patch.dict(
        os.environ,
        {
            "TASKS_CLIENT_ID": "test_client_id",
            "TASKS_CLIENT_SECRET": "test_client_secret",
            "TASKS_REFRESH_TOKEN": "test_refresh_token",
            "TASKS_TOKEN_URI": "https://custom.oauth.com/token",
        },
    )
    def test_init_with_custom_token_uri(
        self,
        mock_request: Any,
        mock_creds_class: Any,
        mock_build: Any,
    ) -> None:
        """Test initialization with custom token URI from environment."""
        # ARRANGE
        mock_creds = Mock(spec=Credentials)
        mock_creds.valid = True
        mock_creds.refresh_token = "test_refresh_token"
        mock_creds.to_json.return_value = (
            '{"mock": "token_data"}'  # Fix: Return a proper JSON string
        )
        mock_creds_class.return_value = mock_creds

        mock_service = Mock()
        mock_build.return_value = mock_service

        # ACT
        GTaskClient()

        # ASSERT
        mock_creds_class.assert_called_once_with(
            None,
            refresh_token="test_refresh_token",
            token_uri="https://custom.oauth.com/token",
            client_id="test_client_id",
            client_secret="test_client_secret",
            scopes=GTaskClient.SCOPES,
        )

    @patch("gtask_client_impl.gtask_impl.build")
    @patch("gtask_client_impl.gtask_impl.Path")  # Add this patch
    @patch("gtask_client_impl.gtask_impl.Credentials")
    @patch("gtask_client_impl.gtask_impl.Request")
    @patch.dict(
        os.environ,
        {
            "TASKS_CLIENT_ID": "test_client_id",
            "TASKS_CLIENT_SECRET": "test_client_secret",
            "TASKS_REFRESH_TOKEN": "test_refresh_token",
        },
    )
    def test_init_env_vars_refresh_failure(
        self,
        mock_request: Any,
        mock_creds_class: Any,
        mock_path: Any,
        mock_build: Any,
    ) -> None:
        """Test handling of refresh failure with environment variables."""
        # ARRANGE
        mock_creds = Mock(spec=Credentials)
        mock_creds.refresh.side_effect = RefreshError("Token expired")  # type: ignore[no-untyped-call]
        mock_creds_class.return_value = mock_creds

        mock_service = Mock()
        mock_build.return_value = mock_service

        # Mock Path to prevent finding local token file
        mock_path.return_value.exists.return_value = False  # Add this line

        # ACT & ASSERT - Should now raise error instead of falling back to interactive
        with pytest.raises(
            RuntimeError,
            match="No valid credentials found and interactive mode is disabled",
        ):
            GTaskClient()

    @patch("gtask_client_impl.gtask_impl.build")
    @patch("gtask_client_impl.gtask_impl.Path")
    @patch("gtask_client_impl.gtask_impl.Credentials")
    def test_init_with_token_file_success(
        self,
        mock_creds_class: Any,
        mock_path: Any,
        mock_build: Any,
    ) -> None:
        """Test successful initialization with token file."""
        # ARRANGE
        # Mock environment to not have credentials
        with patch.dict(os.environ, {}, clear=True):
            mock_token_path = Mock()
            mock_token_path.exists.return_value = True
            mock_path.return_value = mock_token_path

            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = True
            mock_creds.refresh_token = "file_token"
            mock_creds_class.from_authorized_user_file.return_value = mock_creds

            mock_service = Mock()
            mock_build.return_value = mock_service

            # ACT
            client = GTaskClient()

            # ASSERT
            mock_creds_class.from_authorized_user_file.assert_called_once_with(
                "token.json",
                GTaskClient.SCOPES,
            )
            assert client.service is mock_service

    @patch("gtask_client_impl.gtask_impl.build")
    @patch("gtask_client_impl.gtask_impl.Path")
    @patch("gtask_client_impl.gtask_impl.Credentials")
    @patch("gtask_client_impl.gtask_impl.Request")
    def test_init_token_file_needs_refresh(
        self,
        mock_request: Any,
        mock_creds_class: Any,
        mock_path: Any,
        mock_build: Any,
    ) -> None:
        """Test token file that needs refresh."""
        # ARRANGE
        with patch.dict(os.environ, {}, clear=True):
            mock_token_path = Mock()
            mock_token_path.exists.return_value = True
            mock_path.return_value = mock_token_path

            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = False
            mock_creds.refresh_token = "file_token"
            mock_creds_class.from_authorized_user_file.return_value = mock_creds

            # After refresh, make it valid
            def refresh_effect(request: Any) -> None:
                mock_creds.valid = True

            mock_creds.refresh.side_effect = refresh_effect

            mock_service = Mock()
            mock_build.return_value = mock_service

            # ACT
            client = GTaskClient()

            # ASSERT
            mock_creds.refresh.assert_called_once()
            assert client.service is mock_service

    @patch("gtask_client_impl.gtask_impl.build")
    def test_init_interactive_mode_forces_flow(self, mock_build: Any) -> None:
        """Test that interactive=True forces interactive flow."""
        # ARRANGE
        mock_service = Mock()
        mock_build.return_value = mock_service

        with patch.object(GTaskClient, "_run_interactive_flow") as mock_interactive:
            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = True
            mock_creds.refresh_token = "interactive_token"
            mock_interactive.return_value = mock_creds

            with patch.object(GTaskClient, "_save_token") as mock_save:
                # ACT
                GTaskClient(interactive=True)

                # ASSERT
                mock_interactive.assert_called_once_with("credentials.json")
                mock_save.assert_called_once_with(mock_creds, "token.json")

    def test_init_no_valid_credentials_raises_error(self) -> None:
        """Test that initialization raises error when no valid credentials found."""
        # ARRANGE
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("gtask_client_impl.gtask_impl.Path") as mock_path,
        ):
            mock_token_path = Mock()
            mock_token_path.exists.return_value = False
            mock_path.return_value = mock_token_path

            with patch.object(GTaskClient, "_run_interactive_flow") as mock_interactive:
                mock_interactive.return_value = None

                # ACT & ASSERT
                with pytest.raises(
                    RuntimeError,
                    match="No valid credentials found and interactive mode is disabled",
                ):
                    GTaskClient()

    @patch("gtask_client_impl.gtask_impl.build")
    def test_build_service_failure(self, mock_build: Any) -> None:
        """Test handling of build service failure."""
        # ARRANGE
        mock_build.side_effect = Exception("Service build failed")

        with patch.object(GTaskClient, "_run_interactive_flow") as mock_interactive:
            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = True
            mock_creds.to_json.return_value = '{"fake": "token"}'  # Add this line
            mock_interactive.return_value = mock_creds

            # ACT & ASSERT
            with pytest.raises(Exception, match="Service build failed"):
                GTaskClient(interactive=True)


class TestGTaskClientHelperMethods:
    """Test cases for GTaskClient helper methods."""

    @patch("gtask_client_impl.gtask_impl.InstalledAppFlow")
    @patch("gtask_client_impl.gtask_impl.Path")
    def test_run_interactive_flow_success(self, mock_path: Any, mock_flow_class: Any) -> None:
        """Test successful interactive OAuth flow."""
        # ARRANGE
        mock_creds_path = Mock()
        mock_creds_path.exists.return_value = True
        mock_path.return_value = mock_creds_path

        mock_flow = Mock()
        mock_creds = Mock(spec=Credentials)
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_class.from_client_secrets_file.return_value = mock_flow

        client = GTaskClient(service=Mock())  # Skip normal init

        # ACT
        result = client._run_interactive_flow("credentials.json")

        # ASSERT
        assert result is mock_creds
        mock_flow_class.from_client_secrets_file.assert_called_once_with(
            "credentials.json",
            GTaskClient.SCOPES,
        )
        mock_flow.run_local_server.assert_called_once_with(port=0)

    @patch("gtask_client_impl.gtask_impl.Path")
    def test_run_interactive_flow_missing_credentials(self, mock_path: Any) -> None:
        """Test interactive flow with missing credentials file."""
        # ARRANGE
        mock_creds_path = Mock()
        mock_creds_path.exists.return_value = False
        mock_path.return_value = mock_creds_path

        client = GTaskClient(service=Mock())  # Skip normal init

        # ACT & ASSERT
        with pytest.raises(FileNotFoundError, match=r"'credentials.json' not found"):
            client._run_interactive_flow("credentials.json")

    @patch("gtask_client_impl.gtask_impl.InstalledAppFlow")
    @patch("gtask_client_impl.gtask_impl.Path")
    def test_run_interactive_flow_exception(self, mock_path: Any, mock_flow_class: Any) -> None:
        """Test interactive flow with exception during flow."""
        # ARRANGE
        mock_creds_path = Mock()
        mock_creds_path.exists.return_value = True
        mock_path.return_value = mock_creds_path

        mock_flow_class.from_client_secrets_file.side_effect = Exception("Flow failed")

        client = GTaskClient(service=Mock())  # Skip normal init

        # ACT & ASSERT
        with pytest.raises(Exception, match="Flow failed"):
            client._run_interactive_flow("credentials.json")

    @patch("gtask_client_impl.gtask_impl.Path")
    def test_save_token_success(self, mock_path: Any) -> None:
        """Test successful token saving."""
        # ARRANGE
        mock_token_path = mock_path.return_value
        mock_file_handle = MagicMock()
        mock_token_path.open.return_value.__enter__.return_value = mock_file_handle

        client = GTaskClient(service=Mock())  # A dummy client to call the method on
        mock_creds = Mock(spec=Credentials)
        mock_creds.to_json.return_value = '{"fake": "token"}'

        # ACT
        client._save_token(mock_creds, "token.json")

        # ASSERT
        mock_token_path.open.assert_called_once_with("w")
        mock_file_handle.write.assert_called_once_with('{"fake": "token"}')

    @patch("gtask_client_impl.gtask_impl.Path")
    def test_save_token_exception(self, mock_path: Any) -> None:
        """Test token saving with exception."""
        # ARRANGE
        mock_token_path = Mock()
        mock_token_path.open.side_effect = Exception("Write failed")
        mock_path.return_value = mock_token_path

        mock_creds = Mock(spec=Credentials)
        client = GTaskClient(service=Mock())  # Skip normal init

        # ACT & ASSERT
        with pytest.raises(Exception, match="Write failed"):
            client._save_token(mock_creds, "token.json")


class TestGTaskClientConstants:
    """Test cases for GTaskClient constants and class attributes."""

    def test_scopes_constant(self) -> None:
        """Test that SCOPES constant is correctly defined."""
        expected_scopes = [
            "https://www.googleapis.com/auth/tasks",
        ]
        assert expected_scopes == GTaskClient.SCOPES

    def test_failure_message_constant(self) -> None:
        """Test that failure message constant is defined."""
        assert (
            GTaskClient.FAILURE_TO_CRED == "Failed to obtain credentials. Please check your setup."
        )
        assert isinstance(GTaskClient.FAILURE_TO_CRED, str)
        assert len(GTaskClient.FAILURE_TO_CRED) > 0
