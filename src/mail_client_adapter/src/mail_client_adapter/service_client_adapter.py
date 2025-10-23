"""Service client adapter implementation."""

import logging
from collections.abc import Iterator
from typing import cast

from dotenv import load_dotenv

import mail_client_api
from mail_client_api import message
from mail_client_service_client import Client as ServiceClient

from .api import (
    delete_message_sync,
    get_message_sync,
    list_messages_sync,
    mark_as_read_sync,
)
from .service_message import ServiceMessage

load_dotenv()


class ServiceClientAdapter(mail_client_api.Client):
    """Adapter that wraps the auto-generated service client to implement the Client protocol."""

    def __init__(self, service_client: ServiceClient) -> None:
        """Initialize the adapter with a service client.

        Args:
            service_client: The authenticated service client to wrap

        """
        self._service_client = service_client
        self.logger = logging.getLogger(__name__)

    def _raise_message_not_found_error(self, message_id: str) -> None:
        """Raise an error when a message is not found."""
        msg = f"Message with ID {message_id} not found"
        raise RuntimeError(msg)

    def get_message(self, message_id: str) -> message.Message:
        """Return a message by its ID.

        Args:
            message_id: The unique identifier of the message

        Returns:
            Message: The requested message

        Raises:
            RuntimeError: If the message cannot be retrieved

        """
        try:
            response = get_message_sync(
                message_id=message_id,
                client=self._service_client,
            )

            if response is None:
                # Raise a runtime error if the message is not found
                self._raise_message_not_found_error(message_id)

            return ServiceMessage(cast("dict[str, str]", response))

        except Exception as e:
            msg = f"Failed to get message {message_id}: {e!s}"
            raise RuntimeError(msg) from e

    def delete_message(self, message_id: str) -> bool:
        """Delete a message by its ID.

        Args:
            message_id: The unique identifier of the message to delete

        Returns:
            bool: True if the message was successfully deleted, False otherwise

        """
        try:
            self.logger.info("Attempting to delete message %s", message_id)
            response = delete_message_sync(
                message_id=message_id,
                client=self._service_client,
            )

            # Check if the response indicates success
            if response is None:
                self.logger.warning(
                    "Received None response when deleting message %s",
                    message_id,
                )
                return False

            # The response should contain success information
            success = response.get(
                "success",
                True,
            )  # Assume success if we got a response
            if not success:
                self.logger.warning(
                    "Delete operation reported failure for message %s",
                    message_id,
                )
                return False

            self.logger.info("Successfully deleted message %s", message_id)
            return True  # noqa: TRY300

        except Exception as e:
            self.logger.exception("Failed to delete message %s", message_id)
            self.logger.debug("Error details: %s", e)
            return False

    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read by its ID.

        Args:
            message_id: The unique identifier of the message to mark as read

        Returns:
            bool: True if the message was successfully marked as read, False otherwise

        """
        try:
            self.logger.info("Attempting to mark message %s as read", message_id)
            response = mark_as_read_sync(
                message_id=message_id,
                client=self._service_client,
            )

            # Check if the response indicates success
            if response is None:
                self.logger.warning(
                    "Received None response when marking message %s as read",
                    message_id,
                )
                return False

            # The response should contain success information
            success = response.get(
                "success",
                True,
            )  # Assume success if we got a response
            if not success:
                self.logger.warning(
                    "Mark as read operation reported failure for message %s",
                    message_id,
                )
                return False

            self.logger.info("Successfully marked message %s as read", message_id)
            return True  # noqa: TRY300

        except Exception as e:
            self.logger.exception("Failed to mark message %s as read", message_id)
            self.logger.debug("Error details: %s", e)
            return False

    def get_messages(self, max_results: int = 10) -> Iterator[message.Message]:
        """Return an iterator of messages from the inbox.

        Args:
            max_results: Maximum number of messages to return

        Yields:
            Message: Messages from the inbox

        """
        try:
            self.logger.info("Fetching messages with max_results=%d", max_results)
            response = list_messages_sync(client=self._service_client)

            if response is None:
                self.logger.warning("Received None response from list_messages_sync")
                return

            # Handle case where response is not a list
            if not isinstance(response, list):
                self.logger.error(
                    "Expected list response but got %s",
                    type(response).__name__,
                )
                return

            # Limit results if max_results is specified and positive
            messages_to_process = response[:max_results] if max_results is not None and max_results > 0 else response

            self.logger.info("Processing %d messages", len(messages_to_process))
            for i, message_item in enumerate(messages_to_process):
                try:
                    yield ServiceMessage(message_item)
                except (TypeError, ValueError, KeyError) as e:
                    self.logger.warning(
                        "Failed to create ServiceMessage for item %d: %s",
                        i,
                        e,
                    )
                    # Continue processing other messages even if one fails
                    continue

        except Exception as e:
            self.logger.exception("Failed to fetch messages")
            self.logger.debug("Error details: %s", e)
            return


def get_service_client_impl(
    *,
    interactive: bool = False,  # noqa: ARG001
    base_url: str = "http://127.0.0.1:8000/",
) -> mail_client_api.Client:
    """Return a configured :class:`ServiceClientAdapter` instance."""
    service_client = ServiceClient(base_url)
    return ServiceClientAdapter(service_client)


def register() -> None:
    """Register the Gmail client implementation with the mail client API."""
    mail_client_api.get_client = get_service_client_impl
