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
from typing import ClassVar

import task_client_api
from google.auth.exceptions import GoogleAuthError, RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[import-untyped]
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

    def __init__(self, service: Resource | None = None, *, interactive: bool = False) -> None:
        """Initialize the GTaskClient, handling authentication."""
        self.logger = logging.getLogger(__name__)
        if service:
            self.service = service
            return  # Skip auth if service is provided

        creds: Credentials | None = None
        token_path = self.TOKEN_PATH
        creds_path = self.CREDENTIALS_PATH

        if interactive:
            creds = self._run_interactive_flow(creds_path)

        if not creds and not interactive:
            creds = self._auth_from_env()

        if not creds and not interactive:
            creds = self._auth_from_token_file(token_path)

        if not creds or (creds and not creds.valid and not creds.refresh_token):
            if not interactive:
                msg = (
                    "No valid credentials found and interactive mode is disabled. "
                    "Please provide valid credentials via environment variables or token file."
                )
                raise RuntimeError(msg)

            creds = self._run_interactive_flow(creds_path)
            if not creds:
                msg = "Interactive authentication failed."
                raise RuntimeError(msg)

        if not creds or not creds.valid:
            raise RuntimeError(self.FAILURE_TO_CRED)

        if interactive or (creds.refresh_token and not Path(token_path).exists()):
            self._save_token(creds, token_path)

        self.service = build("tasks", "v1", credentials=creds)

    def _run_interactive_flow(self, creds_path: str) -> Credentials | None:
        """Run the interactive OAuth flow.

        This method launches a local web server to handle the OAuth2 flow,
        opening the user's browser to complete authentication with Google.
        """
        if not Path(creds_path).exists():
            msg = f"'{creds_path}' not found. Cannot run interactive auth."
            raise FileNotFoundError(msg)
        flow = InstalledAppFlow.from_client_secrets_file(
            creds_path,
            self.SCOPES,
        )
        return flow.run_local_server(port=0)  # type: ignore[no-any-return]

    def _auth_from_env(self) -> Credentials | None:
        """Attempt to authenticate using environment variables.

        Expected environment variables:
            TASKS_CLIENT_ID, TASKS_CLIENT_SECRET, TASKS_REFRESH_TOKEN
            optional: TASKS_TOKEN_URI

        Returns:
            A refreshed Credentials object on success, or None on failure.

        """
        client_id = os.environ.get("TASKS_CLIENT_ID")
        client_secret = os.environ.get("TASKS_CLIENT_SECRET")
        refresh_token = os.environ.get("TASKS_REFRESH_TOKEN")
        token_uri = os.environ.get("TASKS_TOKEN_URI", "https://oauth2.googleapis.com/token")

        if not (client_id and client_secret and refresh_token):
            return None

        try:
            creds = Credentials(  # type: ignore[no-untyped-call]
                None,
                refresh_token=refresh_token,
                token_uri=token_uri,
                client_id=client_id,
                client_secret=client_secret,
                scopes=self.SCOPES,
            )
            creds.refresh(Request())  # type: ignore[no-untyped-call]
            return creds  # noqa: TRY300
        except (GoogleAuthError, RefreshError, OSError, ValueError):
            return None

    def _auth_from_token_file(self, token_path: str) -> Credentials | None:
        """Attempt to load credentials from a token file and refresh if needed.

        Args:
            token_path: Path to token file.

        Returns:
            A valid Credentials object or None if loading/refresh fails.

        """
        try:
            if not Path(token_path).exists():
                return None

            creds = Credentials.from_authorized_user_file(  # type: ignore[no-untyped-call]
                token_path,
                self.SCOPES,
            )

            if creds and not creds.valid and creds.refresh_token:
                try:
                    creds.refresh(Request())  # type: ignore[no-untyped-call]
                except (GoogleAuthError, RefreshError, OSError, ValueError):
                    return None
        except (GoogleAuthError, RefreshError, OSError, ValueError):
            return None

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

    """   TASKLIST OPERATIONS   """

    def delete_tasklist(self, tasklist_id: str) -> bool:
        """Delete a tasklist by its ID.

        Args:
            tasklist_id: The ID of the tasklist to delete.

        Returns:
            True if the tasklist was successfully deleted, False otherwise.

        """
        try:
            (
                self.service.tasklists()  # type: ignore[attr-defined]
                .delete(tasklist=tasklist_id)
                .execute()
            )
        except (HttpError, OSError, ValueError) as e:
            self.logger.exception("Failed to delete tasklist %s", tasklist_id)
            self.logger.debug("Error details: %s", e)
            return False
        else:
            return True

    def insert_tasklist(self, title: str) -> tasklist.TaskList:
        """Insert a tasklist.

        Args:
            title: The name of the new tasklist.

        Returns:
            The inserted tasklist with updated fields (e.g., id, etag).

        """
        try:
            body = {"title": title}
            result = (
                self.service.tasklists()  # type: ignore[attr-defined]
                .insert(body=body)
                .execute()
            )
            # Convert result dict to JSON string for raw_data
            raw_data = json.dumps(result)
            return task_client_api.tasklist.get_tasklist(
                task_list_id=result["id"],
                raw_data=raw_data,
            )
        except (HttpError, OSError, ValueError) as e:
            self.logger.exception("Failed to insert tasklist")
            self.logger.debug("Error details: %s", e)
            raise

    def list_tasklists(self) -> list[tasklist.TaskList]:
        """List all tasklists.

        Returns:
            A list of TaskList objects.

        """
        try:
            result = (
                self.service.tasklists().list().execute()  # type: ignore[attr-defined]
            )
            tasklists = []
            for item in result.get("items", []):
                raw_data = json.dumps(item)
                tasklists.append(
                    tasklist.get_tasklist(
                        task_list_id=item["id"],
                        raw_data=raw_data,
                    )
                )
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
                        task_id=item["id"],
                        raw_data=raw_data,
                    )
                )
        except (HttpError, OSError, ValueError) as e:
            self.logger.exception("Failed to list tasks for tasklist %s", tasklist_id)
            self.logger.debug("Error details: %s", e)
            return []
        else:
            return tasks

    def insert_task(self, tasklist_id: str, task_input: dict[str, str | bool | None]) -> task.Task:
        """Insert a task into a tasklist.

        Args:
            tasklist_id: The ID of the tasklist to insert the task into.
            task_input: Dictionary of task fields
                        (e.g., title, notes, status, due, parent, previous).

        Returns:
            The inserted task with updated fields.

        """
        try:
            result = (
                self.service.tasks()  # type: ignore[attr-defined]
                .insert(tasklist=tasklist_id, body=task_input)
                .execute()
            )
            raw_data = json.dumps(result)
        except (HttpError, OSError, ValueError) as e:
            self.logger.exception("Failed to insert task")
            self.logger.debug("Error details: %s", e)
            raise
        else:
            self.logger.info("Successfully created task with ID: %s", result["id"])
            return task_client_api.task.get_task(
                task_id=result["id"],
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
            return task.get_task(
                task_id=task_id,
                raw_data=raw_data,
            )


def get_client_impl(*, interactive: bool = False) -> task_client_api.Client:
    """Return a configured :class:`GTaskClient` instance."""
    return GTaskClient(interactive=interactive)


def register() -> None:
    """Register the GTask client implementation with the task client API."""
    task_client_api.get_client = get_client_impl
