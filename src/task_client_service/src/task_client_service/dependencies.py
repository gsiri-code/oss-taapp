"""Shared dependencies for the FastAPI service."""

import json
import logging
import os
from typing import Annotated, cast

import gtask_client_impl  # noqa: F401  # Ensure registration happens
from fastapi import Depends, HTTPException, Request
from task_client_api import Client, get_client

# Ensure registration happens
gtask_client_impl.register()

logger = logging.getLogger(__name__)

# Store current request for access from gtask_client_impl
current_request: Request | None = None


def get_task_client(request: Request) -> Client:
    """Get the task client, creating it lazily if needed with session credentials."""
    global current_request
    current_request = request  # Store for access from gtask_client_impl

    # Extract credentials from session if available
    session_creds = None
    credentials_json = request.session.get("credentials")  # type: ignore[attr-defined]
    if credentials_json:
        try:
            session_creds = json.loads(credentials_json)
            logger.debug("Found credentials in session")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse session credentials: %s", e)

    # Store session credentials in app state for this request
    # This allows gtask_client_impl to access them without HTTP requests
    if session_creds:
        # Store in app state temporarily for this request
        request.app.state._current_session_creds = session_creds  # type: ignore[attr-defined]
    else:
        request.app.state._current_session_creds = None  # type: ignore[attr-defined]

    # Create a new client per request to ensure it has access to the current session
    # This is necessary because credentials are per-request (session-based)
    try:
        # Set service base URL from request if available
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        os.environ["TASK_SERVICE_BASE_URL"] = base_url

        client = get_client(interactive=False)
        logger.debug("Task client created for request")
        return client
    except RuntimeError as e:
        # RuntimeError means no credentials - this is expected before authentication
        # The client should still be created (with service=None), so this shouldn't happen
        # But if it does, log it and re-raise as HTTPException
        logger.warning("Task client initialization failed: %s", e)
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please authenticate via /auth/login first.",
        ) from e
    except Exception as e:
        logger.exception("Failed to initialize task client")
        raise HTTPException(
            status_code=503,
            detail="Task client not available. Please authenticate via /auth/login first.",
        ) from e


# Define a type alias for reuse (from FastAPI docs)
TaskClientDep = Annotated[Client, Depends(get_task_client)]
