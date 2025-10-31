"""Router for task operations."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any, NotRequired, Required, TypedDict

from fastapi import APIRouter, Body, HTTPException

from task_client_api import Task

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
    """List all tasks under a tasklist."""
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
    """Get a task by ID under a tasklist."""
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
        logger.info("Successfully got task '%s' from tasklist '%s'", task_id, tasklist_id)
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

def _get_str(d: dict[str, Any], key: str, default: str | None = None) -> str | None:
    v = d.get(key)
    if isinstance(v, str):
        return v
    return default

def _get_bool(d: dict[str, Any], key: str) -> bool | None:
    v = d.get(key)
    return v if isinstance(v, bool) else None

@router.post("/{tasklist_id}")
async def insert_task(
    client: TaskClientDep,
    tasklist_id: str,
        task_input: Annotated[
            dict[str, str | None | bool],
            Body(
                examples=[{
                    "summary": "Basic",
                    "value": {
                        "title": "My New Task",
                        "notes": "This is a new task",
                        "status": "needsAction",
                        "due": "2025-11-15T00:00:00.000Z",
                    },
                }]
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
        if task_input.get("due"):
            due_value = task_input["due"]
            if isinstance(due_value, str):
                try:
                    # Let it raise if 'Z' is not accepted; we just validate format.
                    datetime.fromisoformat(due_value)
                except ValueError as err:
                    msg = f"Invalid RFC 3339 timestamp format: {due_value}"
                    raise ValueError(msg) from err

        new_task_obj = _NewTask(
            id=None,
            title=_get_str(task_input, "title", "") or "",
            notes=_get_str(task_input, "notes"),
            due=_get_str(task_input, "due"),
            completed=_get_str(task_input, "completed"),
            status=_get_str(task_input, "status"),
            deleted=_get_bool(task_input, "deleted"),
            hidden=_get_bool(task_input, "hidden"),
        )
        # _NewTask is not the exact nominal type of tasks_api.Task, so silence type check here
        new_task = client.insert_task(tasklist_id, new_task_obj)  # type: ignore[arg-type]
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
    """Delete a task by ID under a tasklist."""
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
        logger.info("Successfully deleted task '%s' from tasklist '%s'", task_id, tasklist_id)
        return {"detail": f"Task '{task_id}' deleted from tasklist '{tasklist_id}'."}


class CreateTaskBody(TypedDict):
    """Schema for creating a new task."""

    title: Required[str]
    notes: NotRequired[str | None]
    status: NotRequired[str | None]  # "needsAction" | "completed"
    due: NotRequired[str | None]  # RFC3339 timestamp
    parent: NotRequired[str | None]
    previous: NotRequired[str | None]
