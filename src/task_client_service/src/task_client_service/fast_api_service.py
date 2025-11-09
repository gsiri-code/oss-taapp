"""FastAPI service for task client operations."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import gtask_client_impl  # noqa: F401
from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from task_client_api import get_client

from task_client_service.routers import auth_router, task_router, tasklist_router

load_dotenv()

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

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))

# Include routers
app.include_router(auth_router)
app.include_router(tasklist_router)
app.include_router(task_router)
