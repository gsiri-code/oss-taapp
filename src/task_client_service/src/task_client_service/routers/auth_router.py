"""Router for authentication operations."""

import json
import logging
import os
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


SCOPES = ["https://www.googleapis.com/auth/tasks"]
CREDENTIALS_PATH = "credentials.json"
REDIRECT_URI = os.environ.get(
    "OAUTH_REDIRECT_URI", "http://127.0.0.1:8000/auth/callback"
)


def get_credentials_path() -> Path:
    """Safely retrieve credentials  path."""
    creds_path = Path(CREDENTIALS_PATH)

    if not creds_path.exists():
        msg = f"'{CREDENTIALS_PATH}' not found. Cannot run OAuth flow."
        logger.error(msg)
        raise HTTPException(status_code=500, detail=msg)
    return creds_path


def credentials_to_dict(creds: Credentials) -> dict[str, Any]:
    """Convert a Credentials object to a JSON-serializable dictionary."""
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }


def _get_creds_from_ext_service(request: Request) -> dict[str, str]:
    """Retrieve token data from Google API using OAuth 2.0 workflow."""
    creds_path = get_credentials_path()

    code = request.query_params.get("code")

    if not code:
        msg = "No authorization code provided. OAuth flow must be initiated via /auth/login"
        logger.error(msg)
        raise HTTPException(status_code=400, detail=msg)

    state: str | None = request.query_params.get("state")
    stored_state: str | None = request.session.pop("oauth_state", None)

    if not stored_state or state != stored_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    try:
        flow: Flow = Flow.from_client_secrets_file(
            str(creds_path),
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )

        flow.fetch_token(code=code, state=state)
        creds: Credentials = flow.credentials

        session_data = credentials_to_dict(creds)

        request.session["credentials"] = json.dumps(session_data)  # type: ignore[attr-defined]

    except Exception as e:
        logger.exception("Failed to exchange authorization code for tokens")
        raise HTTPException(status_code=500, detail=f"OAuth flow failed: {e!s}") from e
    else:
        logger.info("Successfully obtained credentials from Google OAuth flow")
        return session_data


@router.get("/callback")
async def oauth_callback(request: Request) -> Response:
    """Handle OAuth callback from Google."""
    try:
        _get_creds_from_ext_service(request)
        return Response(
            content="Authentication successful! You can close this window.",
            status_code=200,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("OAuth callback failed")
        raise HTTPException(
            status_code=500, detail=f"OAuth callback failed: {e!s}"
        ) from e


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    """Initiate OAuth 2.0 login flow.

    This endpoint redirects the user to Google's authorization page.
    """
    creds_path = Path(CREDENTIALS_PATH)
    if not creds_path.exists():
        msg = f"'{CREDENTIALS_PATH}' not found. Cannot run OAuth flow."
        logger.error(msg)
        raise HTTPException(
            status_code=500,
            detail=msg,
        )

    try:
        flow: Flow = Flow.from_client_secrets_file(
            str(creds_path),
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )

        authorization_url, state = flow.authorization_url(
            access_type="offline",
            prompt="consent",  # Force consent screen to ensure refresh token
        )
        # Ensure proper typing
        authorization_url = str(authorization_url)
        state = str(state)

        request.session["oauth_state"] = state

    except FileNotFoundError as e:
        msg = f"Credentials file not found: {e}"
        logger.exception(msg)
        raise HTTPException(status_code=500, detail=msg) from e
    except ValueError as e:
        msg = f"Invalid credentials file format: {e}"
        logger.exception(msg)
        raise HTTPException(status_code=500, detail=msg) from e
    except Exception as e:
        logger.exception("Failed to initiate OAuth flow")
        raise HTTPException(
            status_code=500, detail=f"Failed to initiate OAuth flow: {e!s}"
        ) from e
    else:
        return RedirectResponse(url=authorization_url, status_code=302)


@router.get("/_give_session_creds")
async def give_session_creds(request: Request) -> JSONResponse:
    """Retrieve session credentials (internal endpoint, not user-facing)."""
    if not hasattr(request, "session"):
        logger.warning("Session middleware not configured")
        raise HTTPException(status_code=500, detail="Session not available")

    creds = request.session.get("credentials")

    if not creds:
        logger.info("No credentials found in session for user")
        raise HTTPException(
            status_code=401,
            detail="No active session found. Please log in at /auth/login",
        )

    return JSONResponse(json.loads(creds))
