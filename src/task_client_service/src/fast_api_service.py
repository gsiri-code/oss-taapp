"""FastAPI service for task client operations."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

import gtask_client_impl  # noqa: F401
from task_client_api import get_client
from task_router import router as task_router
from tasklist_router import router as tasklist_router

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

# Include routers
app.include_router(tasklist_router)
app.include_router(task_router)


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting FastAPI server...")
    uvicorn.run("fast_api_service:app", host="0.0.0.0", port=8000, reload=True)
