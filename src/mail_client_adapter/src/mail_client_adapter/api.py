"""API functions for mail service."""

from enum import IntEnum
from typing import Any, cast

from mail_client_service_client import Client


class HTTPStatus(IntEnum):
    """HTTP status codes used in the API."""

    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    INTERNAL_SERVER_ERROR = 500


def list_messages_sync(
    *,
    client: Client,
) -> list[dict[str, str]] | None:
    """List Messages.

     Get a list of messages from the mail client.

    Args:
        client: The client to use for the request

    Returns:
        List of message dictionaries

    """
    kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/messages",
    }

    response = client.get_httpx_client().request(**kwargs)

    if response.status_code == HTTPStatus.OK:
        return cast("list[dict[str, str]]", response.json())
    if client.raise_on_unexpected_status:
        msg = f"Unexpected status code: {response.status_code}"
        raise RuntimeError(msg)
    return None


def get_message_sync(
    message_id: str,
    *,
    client: Client,
) -> dict[str, str] | None:
    """Get Message.

     Get a specific message by ID.

    Args:
        message_id: The ID of the message to retrieve
        client: The client to use for the request

    Returns:
        Message dictionary or None if not found

    """
    kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/messages/{message_id}",
    }

    response = client.get_httpx_client().request(**kwargs)

    if response.status_code == HTTPStatus.OK:
        return cast("dict[str, str]", response.json())
    if client.raise_on_unexpected_status:
        msg = f"Unexpected status code: {response.status_code}"
        raise RuntimeError(msg)
    return None


def delete_message_sync(
    message_id: str,
    *,
    client: Client,
) -> dict[str, Any] | None:
    """Delete Message.

     Delete a message by ID by delegating to the mail client implementation.

    Args:
        message_id: The ID of the message to delete
        client: The client to use for the request

    Returns:
        Response dictionary or None if failed

    """
    kwargs: dict[str, Any] = {
        "method": "delete",
        "url": f"/messages/{message_id}",
    }

    response = client.get_httpx_client().request(**kwargs)

    if response.status_code == HTTPStatus.OK:
        return cast("dict[str, Any]", response.json())
    if client.raise_on_unexpected_status:
        msg = f"Unexpected status code: {response.status_code}"
        raise RuntimeError(msg)
    return None


def mark_as_read_sync(
    message_id: str,
    *,
    client: Client,
) -> dict[str, Any] | None:
    """Mark As Read.

     Mark a message as read by delegating to the mail client implementation.

    Args:
        message_id: The ID of the message to mark as read
        client: The client to use for the request

    Returns:
        Response dictionary or None if failed

    """
    kwargs: dict[str, Any] = {
        "method": "post",
        "url": f"/messages/{message_id}/mark-as-read",
    }

    response = client.get_httpx_client().request(**kwargs)

    if response.status_code == HTTPStatus.OK:
        return cast("dict[str, Any]", response.json())
    if client.raise_on_unexpected_status:
        msg = f"Unexpected status code: {response.status_code}"
        raise RuntimeError(msg)
    return None
