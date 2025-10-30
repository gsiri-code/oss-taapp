"""FastAPI service for task client operations."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, cast

from fastapi import Body, Depends, FastAPI, HTTPException, Request

import gtask_client_impl  # noqa: F401
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
        logger.critical(e, exc_info=True)
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


def tasklist_to_dict(tasklist: TaskList) -> dict[str, str]:
    """Convert a TaskList object to a JSON-serializable dictionary."""
    return {
        "id": tasklist.id,
        "title": tasklist.title,
        "etag": tasklist.etag,
        "updated": tasklist.updated,
        "self_link": tasklist.self_link,
    }


def task_to_dict(task: Task) -> dict[str, str | None | bool]:
    """Convert a Task object to a JSON-serializable dictionary."""
    return {
        "id": task.id,
        "title": task.title,
        "notes": task.notes,
        "status": task.status,
        "due": task.due,
        "completed": task.completed,
        "deleted": task.deleted,
        "hidden": task.hidden,
    }


@app.get("/tasklists")
async def list_tasklists(client: TaskClientDep) -> list[dict[str, str]]:
    """Get a list of messages from the mail client."""
    logger.info("Received request to list tasklists")
    try:
        tasklists = client.list_tasklists()
        logger.info("Retrieved %d tasklists", len(tasklists))

        formatted_tasklists: list[dict[str, str]] = []

        formatted_tasklists = [tasklist_to_dict(tasklist) for tasklist in tasklists]

    except Exception as e:
        logger.critical(e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
    else:
        logger.info("Successfully formatted %d tasklists", len(formatted_tasklists))
        return formatted_tasklists


@app.get("/tasks/{tasklist_id}")
async def list_tasks(
    client: TaskClientDep, tasklist_id: str
) -> list[dict[str, str | None | bool]]:
    """Get a list of messages from the mail client."""
    logger.info("Received request to list tasklists")
    try:
        tasks = client.list_tasks(tasklist_id)

        formatted_tasks: list[dict[str, str]] = []

        formatted_tasks = [task_to_dict(task) for task in tasks]

        return formatted_tasks

    except Exception as e:
        logger.critical(e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/tasklists")
async def insert_tasklist(
    client: TaskClientDep,
    title: str = Annotated[str, Body(..., example="My New Task List")],
) -> dict[str, str]:
    """Insert a new tasklist."""
    logger.info("Received request to insert tasklist with title: '%s'", title)
    try:
        new_tasklist = client.insert_tasklist(title)
        logger.info("Successfully created tasklist with ID: %s", new_tasklist.id)

        return tasklist_to_dict(new_tasklist)
    except ValueError as e:
        logger.critical(
            "Conflict: Tasklist with title '%s' already exists", title, exc_info=True
        )
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception as e:
        logger.critical("Error inserting tasklist '%s': %s", title, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.delete("/tasklists/{tasklist_id}")
async def delete_tasklist(
    client: TaskClientDep,
    tasklist_id: str,
) -> dict[str, str]:
    """Delete a tasklist."""
    logger.info("Received request to delete tasklist with ID: '%s'", tasklist_id)
    try:
        # Find the tasklist to delete
        target_tasklist: TaskList | None = None
        tasklists: list[TaskList] = client.list_tasklists()

        if tasklists[0].id == tasklist_id:
            raise HTTPException(
                status_code=400,
                detail="Error: Invalid request cannot delete default tasklist",
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

        logger.info("Successfully deleted tasklist with ID: %s", tasklist_id)

        return {"detail": f"Tasklist '{target_tasklist.id}' deleted."}
    except Exception as e:
        logger.critical(
            "Error deleting tasklist '%s': %s", tasklist_id, e, exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting FastAPI server...")
    uvicorn.run("fast_api_service:app", host="0.0.0.0", port=8000, reload=True)
