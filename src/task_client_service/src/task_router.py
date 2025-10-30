"""Router for task operations."""

import logging
from datetime import datetime

from fastapi import APIRouter, Body, HTTPException

from dependencies import TaskClientDep
from task_client_api import Task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


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


@router.get("/{tasklist_id}")
async def list_tasks(
    client: TaskClientDep,
    tasklist_id: str,
) -> list[dict[str, str | None | bool]]:
    logger.info("Work to list tasks from tasklist '%s'", tasklist_id)
    try:
        tasks = client.list_tasks(tasklist_id)
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
        return [task_to_dict(task) for task in tasks]


@router.get("/{tasklist_id}/{task_id}")
async def get_task(
    client: TaskClientDep,
    tasklist_id: str,
    task_id: str,
) -> dict[str, str | None | bool]:
    logger.info("Work to get task '%s' from tasklist '%s'", task_id, tasklist_id)
    try:
        task = client.get_task(tasklist_id, task_id)
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
        logger.info(
            "Successfully got task '%s' from tasklist '%s'", task_id, tasklist_id
        )
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


@router.post("/{tasklist_id}")
async def insert_task(
    client: TaskClientDep,
    tasklist_id: str,
    task_input: dict[str, str | None | bool] = Body(
        ...,
        example={
            "title": "My New Task",
            "notes": "This is a new task",
            "status": "needsAction",
            "due": "2025-11-15T00:00:00.000Z",
        },
    ),
) -> dict[str, str | bool | None]:
    """Insert a new task into a tasklist."""
    logger.info(
        "Received request to insert task with title: '%s' into tasklist: '%s'",
        task_input.get("title", "Unknown"),
        tasklist_id,
    )
    try:
        if task_input.get("due"):
            due_value = task_input["due"]
            if isinstance(due_value, str):
                try:
                    datetime.fromisoformat(due_value.replace("Z", "+00:00"))
                except ValueError:
                    raise ValueError(f"Invalid RFC 3339 timestamp format: {due_value}")

        new_task = client.insert_task(tasklist_id, task_input)
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

        logger.info("Successfully created task with ID: %s", new_task.id)
        return task_to_dict(new_task)


@router.delete("/{tasklist_id}/{task_id}")
async def delete_task(
    client: TaskClientDep,
    tasklist_id: str,
    task_id: str,
) -> dict[str, str]:

    logger.info("Work to delete task '%s' from tasklist '%s'", task_id, tasklist_id)
    try:
        client.delete_task(tasklist_id, task_id)

    except Exception as e:
        logger.critical(
            "Error deleting task '%s' from tasklist '%s': %s",
            task_id,
            tasklist_id,
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e)) from e

    else:
        logger.info(
            "Successfully deleted task '%s' from tasklist '%s'", task_id, tasklist_id
        )
        return {"detail": f"Task '{task_id}' deleted from tasklist '{tasklist_id}'."}
