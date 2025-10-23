from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from mail_client_service_client import errors
from mail_client_service_client.client import AuthenticatedClient, Client
from mail_client_service_client.models.delete_message_messages_message_id_delete_response_delete_message_messages_message_id_delete import (
    DeleteMessageMessagesMessageIdDeleteResponseDeleteMessageMessagesMessageIdDelete,
)
from mail_client_service_client.models.http_validation_error import HTTPValidationError
from mail_client_service_client.types import Response


def _get_kwargs(
    message_id: str,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": f"/messages/{message_id}",
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[DeleteMessageMessagesMessageIdDeleteResponseDeleteMessageMessagesMessageIdDelete, HTTPValidationError]
]:
    if response.status_code == 200:
        response_200 = DeleteMessageMessagesMessageIdDeleteResponseDeleteMessageMessagesMessageIdDelete.from_dict(
            response.json()
        )

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[
    Union[DeleteMessageMessagesMessageIdDeleteResponseDeleteMessageMessagesMessageIdDelete, HTTPValidationError]
]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    message_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[
    Union[DeleteMessageMessagesMessageIdDeleteResponseDeleteMessageMessagesMessageIdDelete, HTTPValidationError]
]:
    """Delete Message

     Delete a message by ID by delegating to the mail client implementation.

    Args:
        message_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[DeleteMessageMessagesMessageIdDeleteResponseDeleteMessageMessagesMessageIdDelete, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        message_id=message_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    message_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[
    Union[DeleteMessageMessagesMessageIdDeleteResponseDeleteMessageMessagesMessageIdDelete, HTTPValidationError]
]:
    """Delete Message

     Delete a message by ID by delegating to the mail client implementation.

    Args:
        message_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[DeleteMessageMessagesMessageIdDeleteResponseDeleteMessageMessagesMessageIdDelete, HTTPValidationError]
    """

    return sync_detailed(
        message_id=message_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    message_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[
    Union[DeleteMessageMessagesMessageIdDeleteResponseDeleteMessageMessagesMessageIdDelete, HTTPValidationError]
]:
    """Delete Message

     Delete a message by ID by delegating to the mail client implementation.

    Args:
        message_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[DeleteMessageMessagesMessageIdDeleteResponseDeleteMessageMessagesMessageIdDelete, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        message_id=message_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    message_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Optional[
    Union[DeleteMessageMessagesMessageIdDeleteResponseDeleteMessageMessagesMessageIdDelete, HTTPValidationError]
]:
    """Delete Message

     Delete a message by ID by delegating to the mail client implementation.

    Args:
        message_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[DeleteMessageMessagesMessageIdDeleteResponseDeleteMessageMessagesMessageIdDelete, HTTPValidationError]
    """

    return (
        await asyncio_detailed(
            message_id=message_id,
            client=client,
        )
    ).parsed
