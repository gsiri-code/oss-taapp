"""Router for tasklist operations."""

import logging
from typing import Annotated

from dependencies import TaskClientDep
from fastapi import APIRouter, Body, HTTPException

from task_client_api import TaskList

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasklists", tags=["tasklists"])


def tasklist_to_dict(tasklist: TaskList) -> dict[str, str]:
    """Convert a TaskList object to a JSON-serializable dictionary."""
    return {
        "id": tasklist.id,
        "title": tasklist.title,
        "etag": tasklist.etag,
        "updated": tasklist.updated,
        "self_link": tasklist.self_link,
    }


@router.get("")
async def list_tasklists(client: TaskClientDep) -> list[dict[str, str]]:
    """Get a list of tasklists from the task client."""
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


@router.post("")
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
        logger.critical("Conflict: Tasklist with title '%s' already exists", title, exc_info=True)
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception as e:
        logger.critical("Error inserting tasklist '%s': %s", title, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{tasklist_id}")
async def delete_tasklist(
    client: TaskClientDep,
    tasklist_id: str,
) -> dict[str, str]:
    """Delete a tasklist by ID."""
    tasklists = client.list_tasklists()

    if tasklists and tasklists[0].id == tasklist_id:
        raise HTTPException(
            status_code=400,
            detail="Error: Invalid request cannot delete default tasklist",
        )

    target_tasklist = next((tl for tl in tasklists if tl.id == tasklist_id), None)
    if not target_tasklist:
        raise HTTPException(
            status_code=404,
            detail=f"Error: Tasklist '{tasklist_id}' not found",
        )

    try:
        success = client.delete_tasklist(tasklist_id)
    except Exception as e:
        logger.critical(
            "Error deleting tasklist '%s': %s", tasklist_id, e, exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to delete tasklist.") from e

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete tasklist.")

    logger.info("Successfully deleted tasklist with ID: %s", tasklist_id)
    return {"detail": f"Tasklist '{target_tasklist.title}' deleted."}
