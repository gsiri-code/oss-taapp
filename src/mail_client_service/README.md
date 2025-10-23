## Mail Client Service (FastAPI)

A minimal FastAPI service that wires up the workspace `mail-client-api` with the `gmail-client-impl`. It initializes the client on startup to ensure the Gmail implementation registers correctly.

### Available Endpoints

The service provides a RESTful API for email operations, following REST conventions:

#### GET Endpoints

- `GET /messages` - List all messages from the mail client
- `GET /messages/{message_id}` - Retrieve a specific message by ID

#### POST Endpoints

- `POST /messages/{message_id}/mark-as-read` - Mark a message as read

#### DELETE Endpoints

- `DELETE /messages/{message_id}` - Delete a message by ID

All endpoints return JSON responses and use appropriate HTTP status codes:

- `200 OK` - Successful operations
- `404 Not Found` - Invalid paths or empty message IDs
- `500 Internal Server Error` - Client exceptions or server errors

#### Example Usage

```bash
# List all messages
curl http://127.0.0.1:8000/messages

# Get a specific message
curl http://127.0.0.1:8000/messages/msg_12345

# Mark a message as read
curl -X POST http://127.0.0.1:8000/messages/msg_12345/mark-as-read

# Delete a message
curl -X DELETE http://127.0.0.1:8000/messages/msg_12345
```

### Prerequisites

- **Python 3.11+**
- One of:
  - **uv** (recommended)
  - Or plain **pip** in a virtual environment

Note: This repository already contains a `token.json` at the repo root used by the Gmail implementation for non-interactive startup.

### Run with uv (recommended)

1. Install dependencies for this package (and link workspace members):
   ```bash
   uv sync --all-packages --extra dev
   ```
2. Start the FastAPI development server:
   ```bash
   uv run uvicorn mail_client_service.fast_api_service:app --reload --port 8000
   ```
3. Open the docs UI:
   - Swagger UI: `http://127.0.0.1:8000/docs`
   - ReDoc: `http://127.0.0.1:8000/redoc`

### Run with pip + venv

1. Change directory to this package and create a venv:
   ```bash
   cd /Users/faithvillarreal/Desktop/Coursework/OSP/HW1/oss-taapp/src/mail_client_service
   python3.11 -m venv .venv && source .venv/bin/activate
   python -m pip install -U pip
   ```
2. Install this service and its workspace dependencies in editable mode:
   ```bash
   pip install -e ../mail_client_api -e ../gmail_client_impl .
   ```
3. Start the server:
   ```bash
   python -m uvicorn mail_client_service.fast_api_service:app --reload --port 8000
   ```
4. Visit:
   - Swagger UI: `http://127.0.0.1:8000/docs`
   - ReDoc: `http://127.0.0.1:8000/redoc`

### Testing

This service includes comprehensive unit tests for all endpoints using FastAPI's testing best practices.

#### Run Tests with uv

```bash
# Install test dependencies
uv sync --extra test

# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/mail_client_service --cov-report=term-missing

# Run specific test file
uv run pytest src/mail_client_service/tests/test_get_messages.py -v
uv run pytest src/mail_client_service/tests/test_post_message.py -v
uv run pytest src/mail_client_service/tests/test_delete_message.py -v
```

#### Run Tests with pip

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
python -m pytest

# Run tests with coverage
python -m pytest --cov=src/mail_client_service --cov-report=term-missing
```

#### Test Structure

The tests use the following FastAPI testing best practices:

- **Dependency Injection Override**: Tests override the `get_mail_client` dependency with a mock client
- **Centralized Test Configuration**: Uses `conftest.py` for shared test utilities and fixtures
- **Comprehensive Mocking**: Uses `unittest.mock.create_autospec` for type-safe mocks of the Client interface
- **HTTP Status Code Testing**: Uses HTTPStatus enum for consistent status code assertions
- **Edge Case Coverage**: Tests success scenarios, error handling, empty responses, and special characters
- **Fixture-Based Setup**: Uses pytest fixtures for automatic mock reset between tests

#### Test Files and Coverage

Each endpoint group has its own dedicated test file:

- **`test_get_messages.py`** - Tests for GET endpoints

  - List messages (success, empty list, single message)
  - Get specific message (success, not found, client errors)
  - Special character and long content handling
  - Various exception scenarios (RuntimeError, ValueError, ConnectionError)

- **`test_post_message.py`** - Tests for POST endpoints

  - Mark message as read (success, client exceptions, authentication errors)
  - Edge cases (empty message ID, special characters, very long IDs)
  - Network error handling and URL encoding

- **`test_delete_message.py`** - Tests for DELETE endpoints

  - Delete message (success, not found, client exceptions)
  - Error propagation and proper HTTP status codes
  - Special character handling in message IDs

- **`conftest.py`** - Shared test configuration
  - Mock client setup with automatic reset between tests
  - HTTPStatus enum for consistent status code testing
  - Centralized test utilities and helper functions

#### Test Categories

- **Success scenarios**: Normal operation with various message counts and types
- **Error handling**: Client exceptions, runtime errors, authentication failures, and network errors
- **Edge cases**: Empty message lists, special characters, long content, URL encoding
- **HTTP Protocol**: Proper status codes, request/response validation, and REST compliance
- **Unit testing**: Isolated testing of FastAPI logic without actual Gmail API calls

### Notes

- The application imports `gmail_client_impl` and calls `mail_client_api.get_client(interactive=True)` during FastAPI startup to validate registration and basic initialization.
- If Gmail credentials are not present/valid, startup may log an error in environments without `token.json`. In this repo, a `token.json` exists at the root.
- All endpoints delegate operations to the underlying `mail_client_api.Client` implementation, providing a thin REST wrapper over the component functionality.
- Error handling consistently returns HTTP 500 with the original error message for debugging while maintaining API consistency.
- The service follows REST conventions with appropriate HTTP methods (GET for retrieval, POST for actions, DELETE for removal).
