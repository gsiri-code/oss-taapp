"""FastAPI service for mail client operations."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, cast

import gmail_client_impl  # noqa: F401
from fastapi import Depends, FastAPI, HTTPException, Request
from mail_client_api import Client, Message, get_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan and initialize mail client."""
    client = get_client(interactive=False)
    app.state.mail_client = client
    yield


app = FastAPI(
    title="Mail Client Service",
    description="REST API for mail client operations.",
    lifespan=lifespan,
)


# --- Dependency: obtain the mail client ---
def get_mail_client(request: Request) -> Client:
    """Get the already constructed mail client."""
    return cast("Client", request.app.state.mail_client)


# --- Define a type alias for reuse (from FastAPI docs) ---
MailClientDep = Annotated[Client, Depends(get_mail_client)]


def format_message_object(msg: Message) -> dict[str, str]:
    """Convert a Message object into a JSON-serializable dictionary.

    Args:
        msg: A Message instance containing email metadata and body content.

    Returns:
        A dictionary with the message ID, sender, recipient, subject, date,
        and body text, ready for JSON serialization.

    """
    return {
        "id": msg.id,
        "from": msg.from_,
        "to": msg.to,
        "subject": msg.subject,
        "date": msg.date,
        "body": msg.body,
    }


@app.get("/messages")
async def list_messages(client: MailClientDep) -> list[dict[str, str]]:
    """Get a list of messages from the mail client."""
    try:
        messages = client.get_messages()

        return [format_message_object(msg=msg) for msg in messages]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/messages/{message_id}")
async def get_message(client: MailClientDep, message_id: str) -> dict[str, str]:
    """Get a specific message by ID."""
    try:
        msg = client.get_message(message_id)

        return format_message_object(msg=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/messages/{message_id}/mark-as-read")
async def mark_as_read(client: MailClientDep, message_id: str) -> dict[str, str]:
    """Mark a message as read by delegating to the mail client implementation."""
    try:
        client.mark_as_read(message_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    else:
        return {"detail": f"Message {message_id} marked as read."}


@app.delete("/messages/{message_id}")
async def delete_message(client: MailClientDep, message_id: str) -> dict[str, str]:
    """Delete a message by ID by delegating to the mail client implementation."""
    try:
        client.delete_message(message_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    else:
        return {"detail": f"Message {message_id} deleted."}
