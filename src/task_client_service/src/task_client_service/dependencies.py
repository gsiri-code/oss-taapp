"""Shared dependencies for the FastAPI service."""

from typing import Annotated, cast

from fastapi import Depends, Request
from task_client_api import Client


def get_task_client(request: Request) -> Client:
    """Get the already constructed task client."""
    return cast("Client", request.app.state.task_client)


# Define a type alias for reuse (from FastAPI docs)
TaskClientDep = Annotated[Client, Depends(get_task_client)]
