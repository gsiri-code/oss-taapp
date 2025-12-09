# Welcome to the OSS-TAPP

This project is a professional-grade template for a modern Python application, built using a component-based architecture with a clear separation between interface and implementation.

This documentation site provides an overview of the project's architecture, API contracts, and usage guidelines.

## Project Structure

The project is organized into several component libraries:

### Mail Client Libraries

- **[Mail Client API](api/mail_client_api.md)**: Abstract interface for mail operations
- **[Gmail Implementation](api/gmail_client_impl.md)**: Google Gmail API implementation
- **[Mail Service](libraries/mail_client_service.md)**: FastAPI service for mail operations
- **[Mail Service Client](libraries/mail_client_service_client.md)**: Auto-generated service client
- **[Mail Adapter](libraries/mail_client_adapter.md)**: Adapter for service-based mail operations

### Task Client Libraries

- **[Task Client API](libraries/task_client_api.md)**: Abstract interface for task operations
- **[Google Tasks Implementation](libraries/gtask_client_impl.md)**: Google Tasks API implementation
- **[Task Service](libraries/task_client_service.md)**: FastAPI service for task operations
- **[Task Service Client](libraries/task_client_service_client.md)**: Auto-generated service client
- **[Task Adapter](libraries/task_client_adapter.md)**: Adapter for service-based task operations

### Tickets Libraries

- **[Tickets API](libraries/tickets_api.md)**: Abstract interface for ticketing operations
- **[Tickets Implementation](libraries/tickets_client_impl.md)**: Google Tasks-based ticket implementation

## Quick Start

### Mail Client

```python
import gmail_client_impl
from mail_client_api import get_client

client = get_client(interactive=False)
messages = client.list_messages()
```

### Task Client

```python
import gtask_client_impl
from task_client_api import get_client

client = get_client(interactive=False)
tasklists = client.list_tasklists()
```

### Tickets

```python
import gtask_client_impl  # noqa: F401
from tickets_client_impl import TicketsClient

client = TicketsClient(interactive=False)
ticket = client.create_ticket(title="Fix bug", description="Description")
```

## Documentation

Each library has comprehensive documentation accessible through the navigation menu. All libraries include:

- Overview and purpose
- API reference
- Usage examples
- Architecture details
- Testing guidelines
