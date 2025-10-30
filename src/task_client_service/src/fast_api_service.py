"""FastAPI service for task client operations."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, cast

import gtask_client_impl  # noqa: F401
from fastapi import Body, Depends, FastAPI, HTTPException, Request
from task_client_api import Client, Task, TaskList, get_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan and initialize mail client."""
    logger.info("Starting Task Client Service...")
    try:
        client = get_client(interactive=False)
        app.state.task_client = client
        logger.info("Task client initialized successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize task client: {e}")
        raise
    finally:
        logger.info("Shutting down Task Client Service...")


app = FastAPI(
    title="Task Client Service",
    description="REST API for task client operations.",
    lifespan=lifespan,
)


# --- Dependency: obtain the task client ---
def get_task_client(request: Request) -> Client:
    """Get the already constructed task client."""
    return cast("Client", request.app.state.task_client)


# --- Define a type alias for reuse (from FastAPI docs) ---
TaskClientDep = Annotated[Client, Depends(get_task_client)]

"""
TODO: 
implement these:
    - list_tasks
    - insert_task
    - delete_task
    - get_task

Done:
    - def list_tasklists(self) -> list[tasklist.TaskList]:
    - def list_tasklists(self) -> list[tasklist.TaskList]:
    - delete_tasklist


"""


def format_tasklist_object(tasklist: TaskList) -> dict[str, str]:
    """Format a TaskList object into a JSON-serializable dictionary."""
    return {
        "id": tasklist.id,
        "title": tasklist.title,
        "etag": tasklist.etag,
        "updated": tasklist.updated,
        "self_link": tasklist.self_link,
    }


@app.get("/tasklists")
async def list_tasklists(client: TaskClientDep) -> list[dict[str, str]]:
    """Get a list of messages from the mail client."""
    logger.info("Received request to list tasklists")
    try:
        tasklists = client.list_tasklists()
        logger.info(f"Retrieved {len(tasklists)} tasklists")

        formatted_tasklists: list[dict[str, str]] = []

        for tasklist in tasklists:
            formatted_tasklists.append(format_tasklist_object(tasklist))

        logger.info(f"Successfully formatted {len(formatted_tasklists)} tasklists")
        return formatted_tasklists
    except Exception as e:
        logger.error(f"Error listing tasklists: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/tasks/{tasklist_id}")
async def list_tasks(client: TaskClientDep, tasklist_id: str) -> list[dict[str, str]]:
    """Get a list of messages from the mail client."""
    logger.info("Received request to list tasklists")
    try:
        tasklist = client.get_tasklist(tasklist_id)

        client.list_tasks(tasklist)

    except Exception as e:
        logger.error(f"Error listing tasklists: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/tasklists")
async def insert_tasklist(
    client: TaskClientDep,
    title: str = Body(..., example="My New Task List"),
) -> dict[str, str]:
    """Insert a new tasklist."""
    logger.info(f"Received request to insert tasklist with title: '{title}'")
    try:
        new_tasklist = client.insert_tasklist(title)
        logger.info(f"Successfully created tasklist with ID: {new_tasklist.id}")

        return format_tasklist_object(new_tasklist)
    except ValueError as e:
        logger.error(f"Conflict: Tasklist with title '{title}' already exists")
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error inserting tasklist '{title}': {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.delete("/tasklists/{tasklist_id}")
async def delete_tasklist(
    client: TaskClientDep,
    tasklist_id: str,
) -> dict[str, str]:
    """Delete a tasklist."""
    logger.info(f"Received request to delete tasklist with ID: '{tasklist_id}'")
    try:
        # Find the tasklist to delete
        target_tasklist: TaskList | None = None
        tasklists: list[TaskList] = client.list_tasklists()

        if tasklists[0].id == tasklist_id:
            raise HTTPException(
                status_code=400,
                detail=f"Error: Invalid request cannot delete default tasklist",
            )

        # Check if the tasklist exists
        for tasklist in tasklists:
            if tasklist.id == tasklist_id:
                target_tasklist = tasklist
                break

        if not target_tasklist:
            raise HTTPException(
                status_code=404, detail=f"Error: Tasklist '{tasklist_id}' not found"
            )

        success = client.delete_tasklist(tasklist_id)

        if not success:
            raise Exception

        logger.info(f"Successfully deleted tasklist with ID: {tasklist_id}")

        return {"detail": f"Tasklist '{target_tasklist.id}' deleted."}
    except Exception as e:
        logger.error(f"Error deleting tasklist '{tasklist_id}': {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting FastAPI server...")
    uvicorn.run("fast_api_service:app", host="0.0.0.0", port=8000, reload=True)
