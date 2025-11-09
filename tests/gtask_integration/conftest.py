"""Common pytest fixtures for integration tests."""

from __future__ import annotations

import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient
from gtask_client_impl.gtask_impl import GTaskClient
from task_client_service.fast_api_service import app


class _TestGTaskClient(GTaskClient):
    """GTaskClient variant that skips real service initialization."""

    def __init__(self) -> None:
        # Do not call the real initializer, it tries to contact Google.
        self.logger = logging.getLogger("tests.gtask_integration.gtask_client")
        self.service: Any = None

    def _ensure_service_initialized(self) -> None:
        """Override to make test calls no-op."""
        return


@pytest.fixture
def client() -> TestClient:
    """HTTP client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def gtask_client() -> GTaskClient:
    """GTaskClient with init disabled, for tests that need a client object."""
    return _TestGTaskClient()
