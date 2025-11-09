"""FastAPI routers for the task client service."""

from .auth_router import router as auth_router
from .task_router import router as task_router
from .tasklist_router import router as tasklist_router

__all__ = ["auth_router", "task_router", "tasklist_router"]
