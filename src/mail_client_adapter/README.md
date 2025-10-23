# Mail Client Adapter

## Overview
`mail_client_adapter` provides an adapter that wraps the auto-generated mail client service client to implement the `mail_client_api.Client` protocol. The package contains the adapter implementation, factory functions, and comprehensive testing.

## Purpose
- Wrap the auto-generated `mail_client_impl` service client
- Implement the `mail_client_api.Client` protocol for service-based mail operations
- Provide a seamless interface that works whether mail operations are local (library) or remote (service)
- Handle translation between service response models and the expected `Message` interface

## Architecture

### Component Design
The package exposes a `ServiceClientAdapter` class that implements the `mail_client_api.Client` interface by wrapping the auto-generated `Client` from `mail_client_service_client`. It translates method calls to appropriate service endpoints and converts response models to the expected `Message` interface.

### Service Integration
```python
from mail_client_adapter import create_service_adapter

# Create adapter with service configuration
adapter = create_service_adapter(
    base_url="http://localhost:8000",
    token="your-auth-token"
)

# Use as a mail_client_api.Client
for msg in adapter.get_messages(max_results=5):
    subject: str = msg.subject
```

### Factory Pattern
The package provides a factory function for easy instantiation:
```python
from mail_client_adapter import create_service_adapter

adapter = create_service_adapter(
    base_url="http://localhost:8000",
    token="your-auth-token"
)
```

## API Reference

### ServiceClientAdapter Class
```python
class ServiceClientAdapter(Client):
    ...
```

#### Methods
- `get_message(message_id: str) -> Message`: Return a single message from the service
- `delete_message(message_id: str) -> bool`: Remove the message via service call
- `mark_as_read(message_id: str) -> bool`: Mark message as read via service call
- `get_messages(max_results: int = 10) -> Iterator[Message]`: Yield messages from service

### Factory Function
`create_service_adapter(base_url: str, token: str) -> ServiceClientAdapter`: Creates a configured adapter instance with service client.

## Usage Examples

### Basic Operations
```python
from mail_client_adapter import create_service_adapter

adapter = create_service_adapter(
    base_url="http://localhost:8000",
    token="your-auth-token"
)

for message in adapter.get_messages(max_results=3):
    print(f"{message.id}: {message.subject}")
```

### Message Management
```python
from mail_client_adapter import create_service_adapter

adapter = create_service_adapter(
    base_url="http://localhost:8000",
    token="your-auth-token"
)

important = adapter.get_message("important_msg_123")
adapter.mark_as_read(important.id)
```

### Running the Example
```bash
# Set PYTHONPATH and run the example script
PYTHONPATH="/Users/faithvillarreal/Desktop/Coursework/OSP/HW1/oss-taapp/src/mail_client_api/src:/Users/faithvillarreal/Desktop/Coursework/OSP/HW1/oss-taapp/src/mail_client_adapter/src" python src/mail_client_adapter/example_usage.py
```

Or using uv:

```bash
# Using uv with PYTHONPATH
PYTHONPATH="/Users/faithvillarreal/Desktop/Coursework/OSP/HW1/oss-taapp/src/mail_client_api/src:/Users/faithvillarreal/Desktop/Coursework/OSP/HW1/oss-taapp/src/mail_client_adapter/src" uv run src/mail_client_adapter/example_usage.py
```

## Testing
```bash
# Run unit tests (with PYTHONPATH)
PYTHONPATH="/Users/faithvillarreal/Desktop/Coursework/OSP/HW1/oss-taapp/src/mail_client_api/src:/Users/faithvillarreal/Desktop/Coursework/OSP/HW1/oss-taapp/src/mail_client_adapter/src" uv run pytest src/mail_client_adapter/tests/ -q

# Run with coverage
PYTHONPATH="/Users/faithvillarreal/Desktop/Coursework/OSP/HW1/oss-taapp/src/mail_client_api/src:/Users/faithvillarreal/Desktop/Coursework/OSP/HW1/oss-taapp/src/mail_client_adapter/src" uv run pytest src/mail_client_adapter/tests/ --cov=src/mail_client_adapter --cov-report=term-missing

# Run specific test file
PYTHONPATH="/Users/faithvillarreal/Desktop/Coursework/OSP/HW1/oss-taapp/src/mail_client_api/src:/Users/faithvillarreal/Desktop/Coursework/OSP/HW1/oss-taapp/src/mail_client_adapter/src" uv run pytest src/mail_client_adapter/tests/test_service_client_adapter.py -v
```

## Implementation Details

The adapter implements the `mail_client_api.Client` interface by:

1. **Wrapping the auto-generated client**: Uses `Client` from `mail_client_service_client`
2. **Translating method calls**: Maps interface methods to appropriate service endpoints
3. **Converting response models**: Transforms service responses to `Message` interface
4. **Handling errors**: Provides appropriate error handling and fallbacks

This allows the same interface to work whether the mail client runs as a library (direct Gmail API calls) or as a service (network calls to the mail service).
