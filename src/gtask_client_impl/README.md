# Google Tasks Client Implementation

## Overview

`gtask_client_impl` provides a concrete implementation of the `task_client_api.Client` abstraction backed by the Google Tasks API. It handles OAuth2 authentication, manages task and tasklist operations, and returns `GTask` and `GTaskList` objects.

## Purpose

This package serves as the production-ready Google Tasks integration:

- **Google Tasks API Integration**: Connects to Google Tasks using official Google APIs
- **OAuth2 Authentication**: Handles secure authentication with multiple modes (interactive/non-interactive, FastAPI session support)
- **ABC Implementation**: Provides concrete implementation of all Client operations
- **Task & TaskList Management**: Full CRUD operations for tasks and tasklists
- **Dependency Injection**: Automatically registers itself as the Client implementation

## Architecture

### Authentication Modes

The client supports multiple authentication strategies:

1. **FastAPI Session** (when available): Retrieves credentials from FastAPI request context
2. **Environment Variables**: Reads OAuth2 credentials from environment (CI/CD, production)
3. **Local Token File**: Uses `token.json` for development
4. **Interactive Flow**: Launches browser OAuth flow (initial setup only)

Credential priority: FastAPI session → environment variables → `token.json` → interactive flow.

### Dependency Injection

```python
import gtask_client_impl  # registers the factory

from task_client_api import get_client
client = get_client(interactive=False)
```

## API Reference

### GTaskClient

Implements the `task_client_api.Client` abstract base class.

#### TaskList Operations

- `list_tasklists() -> list[TaskList]`: Retrieves all tasklists for the authenticated user
- `insert_tasklist(tasklist: TaskList) -> TaskList`: Creates a new tasklist
- `delete_tasklist(tasklist_id: str) -> bool`: Deletes a tasklist by ID

#### Task Operations

- `list_tasks(tasklist_id: str) -> list[Task]`: Retrieves all tasks in a tasklist
- `get_task(tasklist_id: str, task_id: str) -> Task`: Fetches a single task
- `insert_task(tasklist_id: str, task: Task) -> Task`: Creates a new task
- `delete_task(tasklist_id: str, task_id: str) -> bool`: Deletes a task

### Factory Functions

- `get_client_impl(*, interactive: bool = False) -> Client`: Creates a `GTaskClient` instance
- `get_task_impl(raw_data: str) -> Task`: Creates a `GTask` from JSON data
- `get_tasklist_impl(raw_data: str) -> TaskList`: Creates a `GTaskList` from JSON data

## Usage Examples

### Basic Operations

```python
import gtask_client_impl
from task_client_api import get_client

client = get_client(interactive=False)

# List all tasklists
tasklists = client.list_tasklists()
for tasklist in tasklists:
    print(f"TaskList: {tasklist.title}")

    # List tasks in each tasklist
    tasks = client.list_tasks(tasklist.id)
    for task in tasks:
        print(f"  - {task.title} ({task.status})")
```

### Task Management

```python
import gtask_client_impl
from task_client_api import get_client, task

client = get_client()

# Get first tasklist
tasklist = client.list_tasklists()[0]

# Create a new task
new_task = task.get_task(json.dumps({
    "title": "Complete project documentation",
    "notes": "Write comprehensive README",
    "status": "needsAction",
    "due": "2025-12-31T23:59:59Z"
}))

created_task = client.insert_task(tasklist.id, new_task)
print(f"Created task: {created_task.id}")

# Mark task as completed
completed_task = task.get_task(json.dumps({
    "id": created_task.id,
    "status": "completed"
}))
client.insert_task(tasklist.id, completed_task)
```

### TaskList Management

```python
import gtask_client_impl
from task_client_api import get_client, tasklist

client = get_client()

# Create a new tasklist
new_tasklist = tasklist.get_tasklist(json.dumps({
    "title": "Work Projects"
}))

created = client.insert_tasklist(new_tasklist)
print(f"Created tasklist: {created.id}")

# Delete a tasklist
client.delete_tasklist(created.id)
```

### Error Handling

```python
import gtask_client_impl
from task_client_api import get_client

try:
    client = get_client(interactive=False)
    task = client.get_task("tasklist_id", "task_id")
    print(f"Retrieved: {task.title}")
except ValueError as e:
    print(f"Parse error: {e}")
except RuntimeError as e:
    print(f"Authentication error: {e}")
except Exception as e:
    print(f"API error: {e}")
```

## Authentication Setup

### Development Setup (Interactive)

1. **Google Cloud Console Setup**:

   - Create a project and enable Google Tasks API
   - Create OAuth2 credentials (Desktop application type)
   - Download `credentials.json`

2. **Local Development**:

   ```python
   import gtask_client_impl
   from task_client_api import get_client

   # First run - opens browser for consent
   client = get_client(interactive=True)
   ```

3. **Token Storage**:
   - OAuth2 tokens are saved to `token.json`
   - Subsequent runs use stored tokens
   - Tokens auto-refresh when expired

### Production Setup (Non-Interactive)

1. **Environment Variables**:

   ```bash
   export TASKS_CLIENT_ID="your_client_id"
   export TASKS_CLIENT_SECRET="your_client_secret"
   export TASKS_REFRESH_TOKEN="your_refresh_token"
   export TASKS_TOKEN_URI="https://oauth2.googleapis.com/token"  # optional
   ```

2. **Production Usage**:

   ```python
   import gtask_client_impl
   from task_client_api import get_client

   # Uses environment variables
   client = get_client(interactive=False)
   ```

3. **CI/CD Integration**:
   - Set environment variables in CI/CD pipelines
   - No browser interaction required
   - Tokens refresh automatically

### FastAPI Service Integration

When used within a FastAPI service context, the client automatically retrieves credentials from the request session:

```python
# In FastAPI route handler
from task_client_api import get_client

client = get_client(interactive=False)
# Automatically uses session credentials if available
```

### Credential Sources (Priority Order)

1. **FastAPI Session** (when available in service context)
2. **Environment Variables** (`TASKS_CLIENT_ID`, `TASKS_CLIENT_SECRET`, `TASKS_REFRESH_TOKEN`)
3. **Local Token File** (`token.json`)
4. **Interactive Flow** (`credentials.json`)

## Testing

```bash
uv run pytest src/gtask_client_impl/tests/ -q
uv run pytest src/gtask_client_impl/tests/ --cov=src/gtask_client_impl --cov-report=term-missing
```

- Unit tests use mocks—no real API calls
- Integration tests in `tests/` may require credentials or environment variables
- Edge case tests cover malformed JSON, invalid data, and error conditions

## Google Tasks API Integration

### Scopes Required

The client requests this Google Tasks API scope:

```python
SCOPES = [
    'https://www.googleapis.com/auth/tasks'  # Full access to tasks and tasklists
]
```

### Response Handling

Google Tasks API responses are processed efficiently:

1. **TaskList Operations**: Converts API responses to `GTaskList` instances
2. **Task Operations**: Converts API responses to `GTask` instances
3. **Error Handling**: Raises `ValueError` for malformed JSON data
4. **Type Safety**: Validates and casts API response fields to expected types

## Implementation Details

### GTask

Concrete implementation of `task.Task`:

- Parses JSON data and validates structure
- Raises `ValueError` on malformed JSON
- Provides type-safe access to task properties

### GTaskList

Concrete implementation of `tasklist.TaskList`:

- Parses JSON data and validates structure
- Raises `ValueError` on malformed JSON
- Provides type-safe access to tasklist properties
