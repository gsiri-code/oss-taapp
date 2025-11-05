# Task Client API

## Overview
`task_client_api` defines the `Client` abstract base class that every task client must implement. The package contains the abstraction, factory hooks, and no concrete logic.

## Purpose
- Document the operations available to consumers.
- Provide a single factory (`get_client`) that implementations can override.
- Keep task-type dependencies explicit through the `task_client_api.task` and `task_client_api.tasklist` modules.

## Architecture

### Component Design
The package exposes one abstract base class focused on task operations—create, delete, list, and manage tasks and tasklists. It depends only on the `Task` and `TaskList` abstractions.

### API Integration
```python
from task_client_api import Client, get_client
from task_client_api.task import Task
from task_client_api.tasklist import TaskList

client: Client = get_client()
tasklists = client.list_tasklists()
for tasklist in tasklists:
    tasks = client.list_tasks(tasklist)
```

### Dependency Injection
Implementation packages (for example `gtask_client_impl`) replace the factory at import time:
```python
import gtask_client_impl  # rebinds task_client_api.get_client

from task_client_api import get_client
client = get_client(interactive=False)
```

## API Reference

### Client Abstract Base Class
```python
class Client(ABC):
    ...
```

#### TaskList Operations
- `list_tasklists() -> list[TaskList]`: Return all available task lists.
- `insert_tasklist(tasklist: TaskList) -> TaskList`: Create a new task list.
- `delete_tasklist(tasklist: TaskList) -> bool`: Remove a task list.

#### Task Operations
- `list_tasks(tasklist: TaskList) -> list[Task]`: Return all tasks in a task list.
- `get_task(task_id: str) -> Task`: Return a single task by ID.
- `insert_task(tasklist: TaskList, task: Task, parent: str = None, previous: str = None) -> Task`: Create a new task.
- `delete_task(task_id: str) -> bool`: Remove a task.

### Factory Functions
- `get_client(*, interactive: bool = False) -> Client`: Returns the bound implementation or raises `NotImplementedError` if none registered.
- `get_task(task_id: str, raw_data: str) -> Task`: Returns a Task instance from raw data.
- `get_tasklist(task_list_id: str, raw_data: str) -> TaskList`: Returns a TaskList instance from raw data.

### Task Abstraction
```python
class Task(ABC):
    @property
    def id(self) -> str: ...
    @property
    def title(self) -> str: ...
    @property
    def notes(self) -> str | None: ...
    @property
    def status(self) -> str: ...
    @property
    def due(self) -> str | None: ...
    @property
    def completed(self) -> str | None: ...
    @property
    def deleted(self) -> bool: ...
    @property
    def hidden(self) -> bool: ...
    @property
    def parent(self) -> str | None: ...
    @property
    def position(self) -> str | None: ...
    @property
    def links(self) -> list[dict[str, str]]: ...
    @property
    def web_view_link(self) -> str | None: ...
    @property
    def assignment_info(self) -> dict[str, Any] | None: ...
```

### TaskList Abstraction
```python
class TaskList(ABC):
    @property
    def id(self) -> str: ...
    @property
    def title(self) -> str: ...
    @property
    def etag(self) -> str: ...
    @property
    def updated(self) -> str: ...
    @property
    def self_link(self) -> str: ...
```

## Usage Examples

### Basic Operations
```python
from task_client_api import get_client

client = get_client(interactive=False)
tasklists = client.list_tasklists()
for tasklist in tasklists:
    print(f"TaskList: {tasklist.title}")
    tasks = client.list_tasks(tasklist)
    for task in tasks:
        print(f"  - {task.title} ({task.status})")
```

### Task Management
```python
from task_client_api import get_client
from task_client_api.task import Task
from task_client_api.tasklist import TaskList

client = get_client()
tasklist = client.list_tasklists()[0]  # Get first tasklist

# Create a new task
new_task = client.insert_task(tasklist, task_data)
client.delete_task(new_task.id)
```

### Working with Subtasks
```python
from task_client_api import get_client

client = get_client()
tasklist = client.list_tasklists()[0]

# Create parent task
parent_task = client.insert_task(tasklist, parent_task_data)

# Create subtask
subtask = client.insert_task(tasklist, subtask_data, parent=parent_task.id)
```

## Implementation Checklist
1. Implement every method in the abstract base class.
2. Return objects compatible with `task_client_api.task.Task` and `task_client_api.tasklist.TaskList`.
3. Publish a factory (`get_client_impl`) and assign it to `task_client_api.get_client`.
4. Honour the `interactive` flag (prompting only when `True`).
5. Handle task hierarchy (parent-child relationships).
6. Support task positioning and ordering within tasklists.

## Testing
```bash
uv run pytest src/task_client_api/tests/ -q
uv run pytest src/task_client_api/tests/ --cov=src/task_client_api --cov-report=term-missing
```
