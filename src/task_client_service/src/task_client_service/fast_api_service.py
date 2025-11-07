"""FastAPI service for task client operations."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import gtask_client_impl  # noqa: F401
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Ensure registration happens (import should trigger it, but explicitly call to be sure)
gtask_client_impl.register()

from .auth_router import router as auth_router
from .task_router import router as task_router
from .tasklist_router import router as tasklist_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan and initialize task client."""
    logger.info("Starting Task Client Service...")
    # Don't initialize client during startup - it will be created lazily when needed
    # This allows the service to start even if credentials aren't available yet
    app.state.task_client = None  # type: ignore[attr-defined]
    logger.info("Task Client Service started (client will be initialized on first request)")
    try:
        yield
    finally:
        logger.info("Shutting down Task Client Service...")


app = FastAPI(
    title="Task Client Service",
    description="REST API for task client operations.",
    lifespan=lifespan,
)

# Add session middleware for OAuth flow
secret_key = os.environ.get("SESSION_SECRET_KEY", "your-secret-key-change-in-production")
app.add_middleware(SessionMiddleware, secret_key=secret_key)

# Add CORS middleware if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(tasklist_router)
app.include_router(task_router)
