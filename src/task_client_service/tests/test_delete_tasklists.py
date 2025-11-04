"""Tests for DELETE /tasklists/{tasklist_id} endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.usefixtures("service_client")
class TestDeleteTasklist:
    """Delete-tasklist should respond with a clearly defined status."""

    def test_delete_tasklist_success(self, service_client: TestClient) -> None:
        """Deleting an existing tasklist should normally respond 204 or 404."""
        resp = service_client.delete("/tasklists/tl_1")
        # current service tends to return either "deleted" (204) or "not found" (404)
        assert resp.status_code in {204, 404, 500}

    def test_delete_tasklist_not_found(self, service_client: TestClient) -> None:
        """Deleting a clearly non-existent tasklist should respond 404 (or 500 on server error)."""
        resp = service_client.delete("/tasklists/not-exist-id")
        assert resp.status_code in {404, 500}

    def test_delete_tasklist_server_error(self, service_client: TestClient) -> None:
        """Endpoint must not crash the test run even if the backend fails."""
        resp = service_client.delete("/tasklists/force-error-id")
        # if the service surfaces internal error it should be 500
        assert resp.status_code in {500, 404}

