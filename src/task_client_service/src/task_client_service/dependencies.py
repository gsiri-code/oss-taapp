"""Shared dependencies for the FastAPI service."""

import json
import logging
import os
from contextvars import ContextVar
from typing import Annotated

import gtask_client_impl  # Ensure registration happens
from fastapi import Depends, HTTPException, Request
from task_client_api import Client, get_client

gtask_client_impl.register()

logger = logging.getLogger(__name__)

# Store current request in a context variable (thread-safe alternative to global)
# This allows gtask_impl.py to access the request object to get app.state
current_request: ContextVar[Request | None] = ContextVar(
    "current_request", default=None
)


def get_task_client(request: Request) -> Client:
    """Get the task client, creating it lazily if needed with session credentials."""
    current_request.set(request)

    session_creds = None
    credentials_json = request.session.get("credentials")
    if credentials_json:
        try:
            session_creds = json.loads(credentials_json)
            logger.debug("Found credentials in session")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse session credentials: %s", e)

    request.app.state.current_session_creds = session_creds

    try:
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        os.environ["TASK_SERVICE_BASE_URL"] = base_url

        client = get_client(interactive=False)
        logger.debug("Task client created for request")
    except RuntimeError as e:
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
    else:
        return client


TaskClientDep = Annotated[Client, Depends(get_task_client)]
