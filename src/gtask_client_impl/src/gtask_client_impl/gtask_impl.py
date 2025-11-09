"""Google Tasks Client Implementation.

This module provides a concrete implementation of the task client API using the Google Tasks API.
It handles OAuth2 authentication and provides methods to interact with Google Tasks and TaskLists.

The implementation supports multiple authentication modes:
    - Environment variables (for CI/CD environments)
    - Local token file (for development)
    - Interactive OAuth flow (for initial setup)
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, ClassVar

import requests
import task_client_api
from google.auth.exceptions import GoogleAuthError, RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from task_client_api import task, tasklist

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # If python-dotenv is not available, check if .env file exists
    # and manually load it
    env_path = Path(".env")
    if env_path.exists():
        with env_path.open() as f:
            for raw_line in f:
                line = raw_line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


class GTaskClient(task_client_api.Client):
    """Concrete implementation of the Client abstraction using Google Tasks API.

    This class provides a complete implementation of the mail_client_api.Client abstraction
    using Google's Tasks API. It handles OAuth2 authentication automatically and provides
    methods to interact with Google Tasks.

    Attributes:
        SCOPES: List of OAuth2 scopes required for Gmail API access.
        FAILURE_TO_CRED: Error message for authentication failures.
        service: The authenticated Tasks API service object.

    Authentication Flow:
        1. If `interactive=True`, forces interactive OAuth flow
        2. Try environment variables (TASKS_CLIENT_ID, TASKS_CLIENT_SECRET, TASKS_REFRESH_TOKEN)
        3. Try local token.json file
        4. Fallback to interactive OAuth flow

    Environment Variables:
        - TASKS_CLIENT_ID: OAuth2 client ID
        - TASKS_CLIENT_SECRET: OAuth2 client secret
        - TASKS_REFRESH_TOKEN: OAuth2 refresh token
        - TASKS_TOKEN_URI: OAuth2 token URI (optional, defaults to Google's endpoint)

    """

    TOKEN_PATH: ClassVar[str] = "token.json"  # noqa: S105
    CREDENTIALS_PATH: ClassVar[str] = "credentials.json"
    SCOPES: ClassVar[list[str]] = [
        "https://www.googleapis.com/auth/tasks",
    ]
    FAILURE_TO_CRED = "Failed to obtain credentials. Please check your setup."
    SERVICE_BASE_URL: ClassVar[str] = os.environ.get(
        "TASK_SERVICE_BASE_URL", "http://127.0.0.1:8001"
    )

    def __init__(
        self, service: Resource | None = None, *, interactive: bool = False
    ) -> None:
        """Initialize the GTaskClient, handling authentication."""
        self.logger = logging.getLogger(__name__)
        if service:
            self.service = service
            return  # Skip auth if service is provided

        creds: Credentials | None = None
        token_path = self.TOKEN_PATH

        """ Authentication Flows """
        # Try to get credentials from FastAPI session first
        # If service is not available, fall back to other methods
        creds = None
        try:
            creds = self._get_session_credentials()
        except Exception as e:
            # If service is not available (e.g., during startup), fall back to other methods
            self.logger.debug("Could not get session credentials: %s", e)

        # Fallback to other methods if session credentials are not available
        if not creds and not interactive:
            try:
                creds = self._auth_from_env()
            except (GoogleAuthError, RefreshError, OSError, ValueError) as e:
                self.logger.debug(
                    "Failed to authenticate from environment variables: %s", e
                )

        if not creds and not interactive:
            try:
                creds = self._auth_from_token_file(token_path)
            except (GoogleAuthError, RefreshError, OSError, ValueError) as e:
                self.logger.debug("Failed to authenticate from token file: %s", e)

        if not creds or (creds and not creds.valid and not creds.refresh_token):
            if not interactive:
                self.logger.warning(
                    "No valid credentials found. user must be authenticated. "
                    "Please authenticate via %s/auth/login",
                    self.SERVICE_BASE_URL,
                )
                self.service = None  # type: ignore[assignment]
                return

            msg = (
                "No valid credentials found. Please authenticate via the FastAPI service "
                f"at {self.SERVICE_BASE_URL}/auth/login"
            )
            raise RuntimeError(msg)

        # Refresh credentials if needed
        if creds and not creds.valid and creds.refresh_token:
            try:
                creds.refresh(Request())  # type: ignore[no-untyped-call]
            except (GoogleAuthError, RefreshError, OSError, ValueError) as e:
                self.logger.warning("Failed to refresh credentials: %s", e)
                # Try to get new credentials from session
                creds = self._get_session_credentials()
                if not creds or not creds.valid:
                    msg = "Failed to refresh credentials and no valid session credentials found."
                    raise RuntimeError(msg) from e

        if not creds or not creds.valid:
            raise RuntimeError(self.FAILURE_TO_CRED)

        self.service = build("tasks", "v1", credentials=creds)

    def _get_session_credentials(self) -> Credentials | None:
        """Request credentials from session data in FastAPI Service."""
        try:
            import sys

            try:
                import task_client_service.dependencies as deps_module
            except ImportError:
                self.logger.debug(
                    "task_client_service.dependencies module not available"
                )
                deps_module = None  # type: ignore[assignment]

            if deps_module and hasattr(deps_module, "current_request"):
                request = deps_module.current_request.get()
                if request:
                    self.logger.debug("Found FastAPI request context")
                    creds_data = getattr(
                        request.app.state, "current_session_creds", None
                    )
                    if creds_data:
                        self.logger.info("Found credentials in app state")
                        return self._create_credentials_from_dict(creds_data)
                    self.logger.debug("No credentials in app state (None)")
                else:
                    self.logger.debug("current_request is None")
            else:
                self.logger.debug(
                    "dependencies module not found or no current_request attribute"
                )
        except (AttributeError, ImportError, KeyError) as e:
            # Not in FastAPI context - this is expected when running outside FastAPI
            self.logger.debug(
                "Not in FastAPI context, cannot get session credentials: %s", e
            )
            return None
        except Exception as e:
            self.logger.debug("Could not get credentials from app state: %s", e)
            return None

        # Fallback: Try HTTP request (won't work without session cookie, but kept for compatibility)
        http_unauthorized = 401
        http_ok = 200

        try:
            # Make request to internal endpoint to get session credentials
            response = requests.get(
                f"{self.SERVICE_BASE_URL}/auth/_give_session_creds",
                timeout=5,
            )

            if response.status_code == http_unauthorized:
                # No credentials in session - user needs to authenticate
                self.logger.info(
                    "No credentials found in session. User needs to authenticate."
                )
                return None

            if response.status_code != http_ok:
                self.logger.warning(
                    "Failed to retrieve session credentials: HTTP %d",
                    response.status_code,
                )
                return None

            # Parse credentials from response
            creds_data = response.json()
            return self._create_credentials_from_dict(creds_data)

        except requests.exceptions.RequestException as e:
            # If service is not available (e.g., during startup), return None
            # This allows fallback to other authentication methods
            self.logger.debug(
                "Failed to connect to FastAPI service for session credentials: %s", e
            )
            return None
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            self.logger.warning("Failed to parse session credentials: %s", e)
            return None

    def _create_credentials_from_dict(
        self, creds_data: dict[str, Any]
    ) -> Credentials | None:
        """Create Credentials object from dictionary data."""
        try:
            # Create Credentials object from session data
            creds = Credentials(  # type: ignore[no-untyped-call]
                token=creds_data.get("token"),
                refresh_token=creds_data.get("refresh_token"),
                token_uri=creds_data.get(
                    "token_uri", "https://oauth2.googleapis.com/token"
                ),
                client_id=creds_data.get("client_id"),
                client_secret=creds_data.get("client_secret"),
                scopes=creds_data.get("scopes", self.SCOPES),
            )

            # Refresh if needed
            if not creds.valid and creds.refresh_token:
                try:
                    creds.refresh(Request())  # type: ignore[no-untyped-call]
                except (GoogleAuthError, RefreshError, OSError, ValueError) as e:
                    self.logger.warning("Failed to refresh session credentials: %s", e)
                    return None

        except Exception as e:
            self.logger.warning("Failed to create credentials from dict: %s", e)
            return None
        else:
            return creds

    def _auth_from_env(self) -> Credentials | None:
        """Attempt to authenticate using environment variables.

        Expected environment variables:
            TASKS_CLIENT_ID, TASKS_CLIENT_SECRET, TASKS_REFRESH_TOKEN
            optional: TASKS_TOKEN_URI

        Returns:
            A refreshed Credentials object on success, or None if env vars are not set.

        Raises:
            GoogleAuthError: If authentication fails due to invalid credentials.
            RefreshError: If token refresh fails.
            OSError: If network or system errors occur.
            ValueError: If credential parameters are invalid.

        """
        client_id = os.environ.get("TASKS_CLIENT_ID")
        client_secret = os.environ.get("TASKS_CLIENT_SECRET")
        refresh_token = os.environ.get("TASKS_REFRESH_TOKEN")
        token_uri = os.environ.get(
            "TASKS_TOKEN_URI", "https://oauth2.googleapis.com/token"
        )

        if not (client_id and client_secret and refresh_token):
            return None

        creds = Credentials(  # type: ignore[no-untyped-call]
            None,
            refresh_token=refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=self.SCOPES,
        )
        creds.refresh(Request())  # type: ignore[no-untyped-call]
        return creds

    def _auth_from_token_file(self, token_path: str) -> Credentials | None:
        """Attempt to load credentials from a token file and refresh if needed.

        Args:
            token_path: Path to token file.

        Returns:
            A valid Credentials object or None if token file does not exist.

        Raises:
            GoogleAuthError: If authentication fails due to invalid credentials.
            RefreshError: If token refresh fails.
            OSError: If file I/O or network errors occur.
            ValueError: If credential parameters are invalid.

        """
        if not Path(token_path).exists():
            return None

        creds = Credentials.from_authorized_user_file(  # type: ignore[no-untyped-call]
            token_path,
            self.SCOPES,
        )

        if creds and not creds.valid and creds.refresh_token:
            creds.refresh(Request())  # type: ignore[no-untyped-call]

        return creds  # type: ignore[no-any-return]

    def _save_token(self, creds: Credentials, token_path: str) -> None:
        """Save the credentials token to a file.

        Persists the OAuth2 credentials to a JSON file for future use,
        avoiding the need to re-authenticate on subsequent runs.

        Args:
            creds: The credentials object to save.
            token_path: Path where the token file should be saved.

        Note:
            The token file contains sensitive information and should be kept secure.
            It's automatically added to .gitignore in most project templates.

        """
        with Path(token_path).open("w") as token:
            token.write(creds.to_json())  # type: ignore[no-untyped-call]

    def _ensure_service_initialized(self) -> None:
        """Ensure the service is initialized with valid credentials.

        If service is None, try to get credentials and initialize it.
        Raises RuntimeError if credentials are not available.
        """
        if self.service is None:
            # Try to get credentials again (might have been authenticated since initialization)
            creds = self._get_session_credentials()
            if not creds:
                creds = self._auth_from_env()
            if not creds:
                creds = self._auth_from_token_file(self.TOKEN_PATH)

            if not creds or not creds.valid:
                msg = (
                    "No valid credentials available. Please authenticate via "
                    f"{self.SERVICE_BASE_URL}/auth/login first."
                )
                raise RuntimeError(msg)

            # Refresh if needed
            if not creds.valid and creds.refresh_token:
                try:
                    creds.refresh(Request())  # type: ignore[no-untyped-call]
                except (GoogleAuthError, RefreshError, OSError, ValueError) as e:
                    msg = f"Failed to refresh credentials: {e}"
                    raise RuntimeError(msg) from e

            # Initialize the service
            self.service = build("tasks", "v1", credentials=creds)
            self.logger.info("Service initialized with credentials")

    """   TASKLIST OPERATIONS   """

    def delete_tasklist(self, tasklist_id: str) -> bool:
        """Delete a tasklist by its ID.

        Args:
            tasklist_id: The ID of the tasklist to delete.

        Returns:
            True if the tasklist was successfully deleted, False otherwise.

        """
        self._ensure_service_initialized()
        try:
            (
                self.service.tasklists()  # type: ignore[attr-defined]
                .delete(tasklist=tasklist_id)
                .execute()
            )
        except HttpError as e:
            if e.status_code == 404:
                raise RuntimeError(f"Task list '{tasklist_id}' not found") from e
            elif e.status_code == 401:
                raise RuntimeError("Unauthorized – credentials expired") from e
            else:
                raise RuntimeError(f"Google API error: {e}") from e
        except RefreshError as e:
            raise RuntimeError("Credential or network problem") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error: {e}") from e
        else:
            return True

    def insert_tasklist(self, tasklist: tasklist.TaskList) -> tasklist.TaskList:
        """Insert a tasklist.

        Args:
            tasklist: TaskList carrying the title to create.

        Returns:
            The created TaskList as returned by the API.

        """
        self._ensure_service_initialized()
        try:
            body = {"title": tasklist.title}
            result = (
                self.service.tasklists()  # type: ignore[attr-defined]
                .insert(body=body)
                .execute()
            )
            # Convert result dict to JSON string for raw_data
            raw_data = json.dumps(result)
            return task_client_api.tasklist.get_tasklist(raw_data=raw_data)
        except (HttpError, OSError, ValueError) as e:
            self.logger.exception("Failed to insert tasklist")
            self.logger.debug("Error details: %s", e)
            raise

    def list_tasklists(self) -> list[tasklist.TaskList]:
        """List all tasklists.

        Returns:
            A list of TaskList objects.

        """
        self._ensure_service_initialized()
        try:
            result = (
                self.service.tasklists().list().execute()  # type: ignore[attr-defined]
            )
            tasklists = []
            for item in result.get("items", []):
                raw_data = json.dumps(item)
                tasklists.append(tasklist.get_tasklist(raw_data=raw_data))
        except (HttpError, OSError, ValueError) as e:
            self.logger.exception("Failed to list tasklists")
            self.logger.debug("Error details: %s", e)
            return []
        else:
            return tasklists

    """   TASK OPERATIONS   """

    def list_tasks(self, tasklist_id: str) -> list[task.Task]:
        """List all tasks in a tasklist.

        Args:
            tasklist_id: The ID of the tasklist to list tasks from.

        Returns:
            A list of Task objects.

        """
        self._ensure_service_initialized()
        try:
            result = (
                self.service.tasks()  # type: ignore[attr-defined]
                .list(tasklist=tasklist_id)
                .execute()
            )
            tasks = []
            for item in result.get("items", []):
                raw_data = json.dumps(item)
                tasks.append(
                    task.get_task(
                        raw_data=raw_data,
                    )
                )
        except (HttpError, OSError, ValueError) as e:
            self.logger.exception("Failed to list tasks for tasklist %s", tasklist_id)
            self.logger.debug("Error details: %s", e)
            return []
        else:
            return tasks

    def insert_task(self, tasklist_id: str, task: task.Task) -> task.Task:
        """Insert a task into a tasklist.

        Args:
            tasklist_id: The ID of the tasklist to insert the task into.
            task: Task carrying the title to create.

        Returns:
            The inserted task with updated fields.

        """
        self._ensure_service_initialized()
        try:
            body: dict[str, str | None] = {
                "title": task.title,
            }
            if task.notes:
                body["notes"] = task.notes
            if task.status:
                body["status"] = task.status
            if task.due:
                body["due"] = task.due

            result = (
                self.service.tasks().insert(tasklist=tasklist_id, body=body).execute()  # type: ignore[attr-defined]
            )
            raw_data = json.dumps(result)
        except (HttpError, OSError, ValueError) as e:
            self.logger.exception("Failed to insert task")
            self.logger.debug("Error details: %s", e)
            raise
        else:
            self.logger.info("Successfully created task with ID: %s", result["id"])
            return task_client_api.task.get_task(
                raw_data=raw_data,
            )

    def delete_task(self, tasklist_id: str, task_id: str) -> bool:
        """Delete a task by its ID.

        Note: The Google Tasks API requires both tasklist ID and task ID.
        This implementation attempts to delete from the default "@default" tasklist.
        For more control, use a task object that contains the tasklist reference.

        Args:
            tasklist_id: The ID of the tasklist to delete the task from.
            task_id: The unique identifier of the task to delete.

        Returns:
            True if the task was successfully deleted, False otherwise.

        """
        self._ensure_service_initialized()
        try:
            # Note: Google Tasks API requires tasklist ID, defaulting to "@default"
            # In a production system, you might want to store tasklist_id with tasks
            (
                self.service.tasks()  # type: ignore[attr-defined]
                .delete(tasklist=tasklist_id, task=task_id)
                .execute()
            )
        except (HttpError, OSError, ValueError) as e:
            self.logger.exception("Failed to delete task %s", task_id)
            self.logger.debug("Error details: %s", e)
            return False
        else:
            return True

    def get_task(self, tasklist_id: str, task_id: str) -> task.Task:
        """Get a task by its ID.

        Note: The Google Tasks API requires both tasklist ID and task ID.
        This implementation attempts to get from the default "@default" tasklist.

        Args:
            tasklist_id: The ID of the tasklist to get the task from.
            task_id: The unique identifier of the task to retrieve.

        Returns:
            A Task object containing the task data.

        Raises:
            ValueError: If the task cannot be retrieved.

        """
        self._ensure_service_initialized()
        try:
            result = (
                self.service.tasks()  # type: ignore[attr-defined]
                .get(tasklist=tasklist_id, task=task_id)
                .execute()
            )
            raw_data = json.dumps(result)
        except (HttpError, OSError, ValueError) as e:
            self.logger.exception("Failed to get task %s", task_id)
            self.logger.debug("Error details: %s", e)
            error_msg = f"Failed to retrieve task {task_id}"
            raise ValueError(error_msg) from e
        else:
            return task.get_task(raw_data=raw_data)


def get_client_impl(*, interactive: bool = False) -> task_client_api.Client:
    """Return a configured :class:`GTaskClient` instance."""
    return GTaskClient(interactive=interactive)


def register() -> None:
    """Register the GTask client implementation with the task client API."""
    task_client_api.get_client = get_client_impl
