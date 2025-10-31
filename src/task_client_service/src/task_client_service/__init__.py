"""Task Client Service - FastAPI service for task client operations."""

from .dependencies import TaskClientDep, get_task_client
from .fast_api_service import app
from .task_router import router as task_router
from .tasklist_router import router as tasklist_router

__all__ = [
    "TaskClientDep",
    "app",
    "get_task_client",
    "task_router",
    "tasklist_router",
]
