## Task Client Service (FastAPI)

A FastAPI service that wires up the workspace `task-client-api` with the `gtask-client-impl`. It initializes the task client on startup to ensure the Google Tasks implementation registers correctly.

### Available Endpoints

The service provides a RESTful API for task and tasklist operations, following REST conventions:

#### Tasklist Endpoints

- `GET /tasklists` - List all tasklists from the task client
- `POST /tasklists` - Create a new tasklist
- `DELETE /tasklists/{tasklist_id}` - Delete a tasklist by ID

#### Task Endpoints

- `GET /tasks/{tasklist_id}` - List all tasks within a given tasklist
- `GET /tasks/{tasklist_id}/{task_id}` - Retrieve a specific task by ID from a tasklist
- `POST /tasks/{tasklist_id}` - Create a new task in a tasklist
- `DELETE /tasks/{tasklist_id}/{task_id}` - Delete a task from a tasklist

All endpoints return JSON responses and use appropriate HTTP status codes:

- `200 OK` - Successful operations
- `400 Bad Request` - Invalid request data or attempting to delete default tasklist
- `404 Not Found` - Task or tasklist not found
- `409 Conflict` - Tasklist with the same title already exists
- `500 Internal Server Error` - Client exceptions or server errors

### Prerequisites

- **Python 3.11+**
- **uv** (package manager)

Note: This repository already contains a `token.json` at the repo root used by the Google Tasks implementation for non-interactive startup.

### Running the Service

#### Run with uv (recommended)

1. Install dependencies for this package (and link workspace members):
   ```bash
   uv sync --all-packages --extra dev
   ```
2. Start the FastAPI development server:
   ```bash
   uvicorn task_client_service.fast_api_service:app --reload --port 8001
   ```
3. The service will be available at `http://127.0.0.1:8001`

4. Open the docs UI:
   - Swagger UI: `http://127.0.0.1:8001/docs`

#### Example Usage

```bash
# List all tasklists
curl http://127.0.0.1:8001/tasklists

# Create a new tasklist
curl -X POST http://127.0.0.1:8001/tasklists \
  -H "Content-Type: application/json" \
  -d '{"title": "My New Task List"}'

# List tasks in a tasklist
curl http://127.0.0.1:8001/tasks/tasklist_12345

# Get a specific task
curl http://127.0.0.1:8001/tasks/tasklist_12345/task_67890

# Create a new task
curl -X POST http://127.0.0.1:8001/tasks/tasklist_12345 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My New Task",
    "notes": "This is a new task",
    "status": "needsAction",
    "due": "2025-11-15T00:00:00.000Z"
  }'

# Delete a task
curl -X DELETE http://127.0.0.1:8001/tasks/tasklist_12345/task_67890

# Delete a tasklist
curl -X DELETE http://127.0.0.1:8001/tasklists/tasklist_12345
```

### Testing

This service includes comprehensive unit tests for all endpoints using FastAPI's testing best practices.

#### Run Tests with uv

```bash
# Install test dependencies
uv sync --extra test

# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/task_client_service --cov-report=term-missing
```

### Notes

- The application imports `gtask_client_impl` and calls `task_client_api.get_client(interactive=False)` during FastAPI startup to validate registration and basic initialization.
- If Google Tasks credentials are not present/valid, startup may log an error in environments without `token.json`. In this repo, a `token.json` exists at the root.
- All endpoints delegate operations to the underlying `task_client_api.Client` implementation, providing a thin REST wrapper over the component functionality.
- Error handling consistently returns appropriate HTTP status codes with error messages for debugging while maintaining API consistency.
- The service follows REST conventions with appropriate HTTP methods (GET for retrieval, POST for creation, DELETE for removal).
- The default tasklist cannot be deleted and will return a 400 Bad Request error if attempted.
