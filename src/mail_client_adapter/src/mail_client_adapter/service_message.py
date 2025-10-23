"""Simple models for API responses."""

import mail_client_api
from mail_client_api import message


class ServiceMessage(message.Message):
    """Message implementation that wraps service response data."""

    def __init__(self, message_data: dict[str, str]) -> None:
        """Initialize with message data from service response.

        Args:
            message_data: Dictionary containing message fields from service response

        """
        self._data = message_data

    @property
    def id(self) -> str:
        """Return the unique identifier of the message."""
        return self._data.get("id", "")

    @property
    def from_(self) -> str:
        """Return the sender's email address."""
        return self._data.get("from", "")

    @property
    def to(self) -> str:
        """Return the recipient's email address."""
        return self._data.get("to", "")

    @property
    def date(self) -> str:
        """Return the date the message was sent."""
        return self._data.get("date", "")

    @property
    def subject(self) -> str:
        """Return the subject line of the message."""
        return self._data.get("subject", "")

    @property
    def body(self) -> str:
        """Return the plain text content of the message."""
        return self._data.get("body", "")


def get_service_message_impl(
    msg_id: str = "",
    raw_data: str = "",
    data: dict[str, str] | None = None,
) -> mail_client_api.Message:
    """Return an instance of the concrete GmailMessage implementation."""
    if data is None:
        data = {}
    del msg_id, raw_data
    return ServiceMessage(message_data=data)


def register() -> None:
    """Register the Service Message implementation with the message abstraction."""
    message.get_message = get_service_message_impl  # type: ignore[assignment]
    mail_client_api.get_message = get_service_message_impl  # type: ignore[assignment]
    # We are choosing to augment the parameters of get_message as the HTTP response
    # is already a dict[str, str]. Turning the HTTP response from JSON back to str then back
    # to Dict isn't optimal compared to overriding the depedency injected factory functio.
