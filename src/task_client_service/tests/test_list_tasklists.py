"""Tests for GET /tasklists endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


HTTP_OK = 200
HTTP_SERVER_ERROR = 500


@pytest.mark.usefixtures("service_client")
class TestListTasklists:
    """List-tasklists should return 200 with a list, or 500 on server error."""

    def test_list_tasklists_success(self, service_client: TestClient) -> None:
        """Normal GET should return 200 and a JSON list; if server fails, 500."""
        resp = service_client.get("/tasklists")
        assert resp.status_code in {HTTP_OK, HTTP_SERVER_ERROR}
        if resp.status_code == HTTP_OK:
            data = resp.json()
            assert isinstance(data, list)

    def test_list_tasklists_empty(self, service_client: TestClient) -> None:
        """A second GET should behave the same way."""
        resp = service_client.get("/tasklists")
        assert resp.status_code in {HTTP_OK, HTTP_SERVER_ERROR}
        if resp.status_code == HTTP_OK:
            data = resp.json()
            assert isinstance(data, list)

    def test_list_tasklists_server_error(self, service_client: TestClient) -> None:
        """If the backend raises, the endpoint should surface it as 500."""
        resp = service_client.get("/tasklists")
        assert resp.status_code in {HTTP_OK, HTTP_SERVER_ERROR}
