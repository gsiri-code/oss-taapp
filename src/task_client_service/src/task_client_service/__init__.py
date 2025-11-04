"""Task Client Service - FastAPI service for task client operations."""

from .dependencies import get_task_client
from .fast_api_service import app

__all__ = [
    "app",
    "get_task_client",
]
