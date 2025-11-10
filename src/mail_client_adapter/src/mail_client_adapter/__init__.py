"""Mail client adapter package for wrapping auto-generated client."""

import mail_client_api

from .service_client_adapter import (
    ServiceClientAdapter as _ServiceClientAdapter,
)
from .service_client_adapter import (
    get_service_client_impl as get_service_client_impl,
)
from .service_client_adapter import (
    register as _register_service_client,
)
from .service_message import (
    ServiceMessage as _ServiceMessage,
)
from .service_message import (
    get_service_message_impl as get_service_message_impl,
)
from .service_message import (
    register as _register_message,
)

# Explicit re-exports for type checking
ServiceClientAdapter: type[mail_client_api.Client] = _ServiceClientAdapter
ServiceMessage: type[mail_client_api.message.Message] = _ServiceMessage


def register() -> None:
    """Register the ServiceClientAdapter and ServiceMessage implementations."""
    _register_service_client()
    _register_message()


# Dependency Injection happens at import time
register()
