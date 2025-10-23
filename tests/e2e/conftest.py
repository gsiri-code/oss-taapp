"""Configuration for e2e tests to handle dependency injection isolation."""

from typing import Never

import pytest

import mail_client_api


@pytest.fixture(autouse=True)
def reset_dependency_injection() -> None:
    """Reset dependency injection before each test to ensure test isolation.

    This fixture runs automatically before each test function to ensure that
    dependency injection from previous tests doesn't interfere with the current test.
    """
    # Store the original get_client function
    original_get_client = getattr(mail_client_api, "get_client", None)

    # Reset to the original implementation (which raises NotImplementedError)
    def reset_get_client(*, interactive: bool = False) -> Never:
        """Reset to original implementation that raises NotImplementedError."""
        msg = "Dependency injection not properly set up"
        raise NotImplementedError(msg)

    # Set the reset function
    mail_client_api.get_client = reset_get_client

    yield

    # Restore the original function after the test
    if original_get_client:
        mail_client_api.get_client = original_get_client


@pytest.fixture(autouse=True)
def reset_message_dependency_injection() -> None:
    """Reset message dependency injection before each test to ensure test isolation."""
    # Store the original get_message function
    original_get_message = getattr(mail_client_api.message, "get_message", None)

    # Reset to the original implementation (which raises NotImplementedError)
    def reset_get_message(msg_id: str, raw_data: str) -> Never:
        """Reset to original implementation that raises NotImplementedError."""
        msg = "Message dependency injection not properly set up"
        raise NotImplementedError(msg)

    # Set the reset function
    mail_client_api.message.get_message = reset_get_message

    yield

    # Restore the original function after the test
    if original_get_message:
        mail_client_api.message.get_message = original_get_message
