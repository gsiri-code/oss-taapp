"""Router for task operations."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

import gtask_client_impl  # noqa: F401
from fastapi import APIRouter, Body, HTTPException
from task_client_api import Task as ServiceTask
from task_client_api import get_task as get_service_task

from .dependencies import TaskClientDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@dataclass
class _NewTask:
    id: str | None
    title: str
    notes: str | None = None
    due: str | None = None
    completed: str | None = None
    status: str | None = None
    deleted: bool | None = None
    hidden: bool | None = None


def task_to_dict(task: ServiceTask) -> dict[str, str | bool | None]:
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


@router.get("/{tasklist_id}")
async def list_tasks(
    client: TaskClientDep,
    tasklist_id: str,
) -> list[dict[str, str | None | bool]]:
    """List all the tasks within a given tasklist."""
    logger.info("Work to list tasks from tasklist '%s'", tasklist_id)
    try:
        tasks = client.list_tasks(tasklist_id)
        formatted_tasks = [task_to_dict(task) for task in tasks]
    except Exception as e:
        logger.critical(
            "Error listing tasks from tasklist '%s': %s",
            tasklist_id,
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e)) from e
    else:
        logger.info("Successfully listed tasks from tasklist '%s'", tasklist_id)
        return formatted_tasks


@router.get("/{tasklist_id}/{task_id}")
async def get_task(
    client: TaskClientDep,
    tasklist_id: str,
    task_id: str,
) -> dict[str, str | None | bool]:
    """Read a single task from a given tasklist."""
    logger.info("Recievd request to get task '%s' from tasklist '%s'", task_id, tasklist_id)
    try:
        task = client.get_task(tasklist_id, task_id)
        formatted_task = task_to_dict(task)
    except Exception as e:
        logger.critical(
            "Error getting task '%s' from tasklist '%s': %s",
            task_id,
            tasklist_id,
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e)) from e
    else:
        logger.info("Successfully retrieved task '%s' from tasklist '%s'", task_id, tasklist_id)
        return formatted_task


@router.post("/{tasklist_id}")
async def insert_task(
    client: TaskClientDep,
    tasklist_id: str,
    task_input: Annotated[
        dict[str, str | None | bool],
        Body(
            examples=[
                {
                    "title": "My New Task",
                    "notes": "This is a new task",
                    "status": "needsAction",
                    "due": "2025-11-15T00:00:00.000Z",
                }
            ]
        ),
    ],
) -> dict[str, str | bool | None]:
    """Insert a new task into a tasklist."""
    logger.info(
        "Received request to insert task with title: '%s' into tasklist: '%s'",
        task_input.get("title", "Unknown"),
        tasklist_id,
    )
    try:
        if isinstance(task_input["due"], str):
            due_date = datetime.fromisoformat(task_input["due"])
            task_input["due"] = due_date.isoformat()

        raw_data = json.dumps(task_input)

        input_task: ServiceTask = get_service_task(raw_data)

        created_task: ServiceTask = client.insert_task(tasklist_id, input_task)
    except ValueError as e:
        logger.critical(
            "Error inserting task '%s' into tasklist '%s': %s",
            task_input.get("title", "Unknown"),
            tasklist_id,
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=400, detail=str(e)) from e

    except Exception as e:
        logger.critical(
            "Error inserting task '%s' into tasklist '%s': %s",
            task_input.get("title", "Unknown"),
            tasklist_id,
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e)) from e
    else:
        logger.info("Successfully created task with ID: %s", created_task.id)
        return task_to_dict(created_task)


@router.delete("/{tasklist_id}/{task_id}")
async def delete_task(
    client: TaskClientDep,
    tasklist_id: str,
    task_id: str,
) -> dict[str, str]:
    """Mark a task as deleted."""
    logger.info("Recieved request to  delete task '%s' from tasklist '%s'", task_id, tasklist_id)
    if not client.delete_task(tasklist_id, task_id):
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    logger.info("Successfully deleted task '%s' from tasklist '%s'", task_id, tasklist_id)
    return {"detail": f"Task '{task_id}' deleted from tasklist '{tasklist_id}'."}
