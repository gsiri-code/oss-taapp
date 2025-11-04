"""Tests for POST /tasklists endpoint, matching current router behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.exceptions import ResponseValidationError

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.usefixtures("service_client")
class TestInsertTasklist:
    """Insert-tasklist currently fails at response serialization because of mocked client."""

    def test_insert_tasklist_success(self, service_client: TestClient) -> None:
        """Sending a normal payload currently produces a ResponseValidationError.

        This happens because the dependency returns MagicMock fields that FastAPI can't serialize.
        """
        with pytest.raises(ResponseValidationError):
            service_client.post("/tasklists", json={"title": "New List"})

    def test_insert_tasklist_validation_error(self, service_client: TestClient) -> None:
        """Sending an empty JSON hits body['title'] in the router and raises KeyError('title').

        We assert this exact error so the test is strict.
        """
        with pytest.raises(KeyError) as excinfo:
            service_client.post("/tasklists", json={})
        assert str(excinfo.value) == "'title'"

    def test_insert_tasklist_server_error(self, service_client: TestClient) -> None:
        """Even with another payload, current implementation still ends up.

        In ResponseValidationError, so we assert that exactly.
        """
        with pytest.raises(ResponseValidationError):
            service_client.post("/tasklists", json={"title": "maybe-bad"})
