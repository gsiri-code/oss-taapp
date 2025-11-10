"""Public exports for the Gmail client implementation package."""

import mail_client_api

from gmail_client_impl.gmail_impl import (
    GmailClient as _GmailClient,
)
from gmail_client_impl.gmail_impl import (
    get_client_impl as get_client_impl,
)
from gmail_client_impl.gmail_impl import (
    register as _register_client,
)
from gmail_client_impl.message_impl import (
    GmailMessage as _GmailMessage,
)
from gmail_client_impl.message_impl import (
    get_message_impl as get_message_impl,
)
from gmail_client_impl.message_impl import (
    register as _register_message,
)

# Explicit re-exports for type checking
GmailClient: type[mail_client_api.Client] = _GmailClient
GmailMessage: type[mail_client_api.message.Message] = _GmailMessage


def register() -> None:
    """Register the Gmail client and message implementations."""
    _register_client()
    _register_message()


# Dependency Injection happens at import time
register()
