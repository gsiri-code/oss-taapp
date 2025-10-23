"""Mail client adapter package for wrapping auto-generated client."""

from .service_client_adapter import (
    ServiceClientAdapter,
    get_service_client_impl,
)
from .service_client_adapter import (
    register as _register_service_client,
)
from .service_message import (
    ServiceMessage,
    get_service_message_impl,
)
from .service_message import (
    register as _register_message,
)

__all__ = ["ServiceClientAdapter", "ServiceMessage", "get_service_client_impl", "get_service_message_impl", "register"]


def register() -> None:
    """Register the ServiceClientAdapter and ServiceMessage implementations."""
    _register_service_client()
    _register_message()


# Dependency Injection happens at import time
register()
