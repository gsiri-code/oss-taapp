"""Router for authentication operations."""
import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# OAuth 2.0 configuration
SCOPES = ["https://www.googleapis.com/auth/tasks"]
CREDENTIALS_PATH = "credentials.json"
# Default redirect URI - can be overridden with OAUTH_REDIRECT_URI env var
# Note: This should match the port your service is running on
# Using 127.0.0.1 instead of localhost for better browser compatibility
REDIRECT_URI = os.environ.get(
    "OAUTH_REDIRECT_URI", "http://127.0.0.1:8001/auth/callback"
)


def _get_creds_from_ext_service(request: Request) -> Credentials:
    """Retrieve token data from Google API using OAuth 2.0 workflow.

    This function handles the OAuth 2.0 authorization code flow with Google.
    It stores the token in the session data.

    Args:
        request: FastAPI request object containing session data.

    Returns:
        Credentials object containing OAuth tokens.

    Raises:
        HTTPException: If credentials file is not found or OAuth flow fails.

    """
    creds_path = Path(CREDENTIALS_PATH)
    if not creds_path.exists():
        msg = f"'{CREDENTIALS_PATH}' not found. Cannot run OAuth flow."
        logger.error(msg)
        raise HTTPException(status_code=500, detail=msg)

    # Check if we have an authorization code in the query parameters
    code = request.query_params.get("code")

    if code:
        # Exchange authorization code for tokens
        try:
            # Get the state parameter from the callback to verify
            state = request.query_params.get("state")
            stored_state = request.session.get("oauth_state")  # type: ignore[attr-defined]
            
            # Recreate the flow with the same configuration used in /auth/login
            # Note: We need to use the same scopes, but Google may return additional scopes
            # if include_granted_scopes="true" was set. The Flow will accept additional scopes
            # as long as the requested ones are included.
            flow = Flow.from_client_secrets_file(
                str(creds_path),
                scopes=SCOPES,  # Requested scopes
                redirect_uri=REDIRECT_URI,
            )
            
            # Fetch token - Google may return additional scopes if user previously granted them
            # This is expected when include_granted_scopes="true" is set
            flow.fetch_token(code=code, state=state)  # type: ignore[no-untyped-call]
            creds = flow.credentials  # type: ignore[attr-defined]

            # Accept whatever scopes Google returns (will include at least the requested scopes)
            # Store credentials in session
            session_data = {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes,  # Use actual scopes returned by Google
            }
            request.session["credentials"] = json.dumps(session_data)  # type: ignore[attr-defined]
            
            # Clear the OAuth state from session
            if "oauth_state" in request.session:  # type: ignore[attr-defined]
                del request.session["oauth_state"]  # type: ignore[attr-defined]

            logger.info("Successfully obtained credentials from Google OAuth flow")
            logger.info("Granted scopes: %s", creds.scopes)
            return creds
        except Exception as e:
            logger.exception("Failed to exchange authorization code for tokens")
            raise HTTPException(status_code=500, detail=f"OAuth flow failed: {e!s}") from e
    else:
        msg = "No authorization code provided. OAuth flow must be initiated via /auth/login"
        logger.error(msg)
        raise HTTPException(status_code=400, detail=msg)


@router.get("/callback")
async def oauth_callback(request: Request) -> Response:
    """Handle OAuth callback from Google.

    This endpoint is called by Google after user authorization.
    It completes the OAuth flow and stores credentials in session.
    """
    try:
        _get_creds_from_ext_service(request)
        # If we get here, credentials were successfully stored
        return Response(
            content="Authentication successful! You can close this window.",
            status_code=200,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("OAuth callback failed")
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {e!s}") from e


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
        flow = Flow.from_client_secrets_file(
            str(creds_path),
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )
        authorization_url, state = flow.authorization_url(  # type: ignore[no-untyped-call]
            access_type="offline",
            prompt="consent",  # Force consent screen to ensure refresh token
        )

        # Store state in session for verification
        request.session["oauth_state"] = state  # type: ignore[attr-defined]

        logger.info("Redirecting to Google OAuth authorization URL: %s", authorization_url[:100])
        # Use status_code=302 for browser compatibility
        return RedirectResponse(url=authorization_url, status_code=302)
    except FileNotFoundError as e:
        msg = f"Credentials file not found: {e}"
        logger.error(msg)
        raise HTTPException(status_code=500, detail=msg) from e
    except ValueError as e:
        msg = f"Invalid credentials file format: {e}"
        logger.error(msg)
        raise HTTPException(status_code=500, detail=msg) from e
    except Exception as e:
        logger.exception("Failed to initiate OAuth flow")
        raise HTTPException(
            status_code=500, detail=f"Failed to initiate OAuth flow: {e!s}"
        ) from e

@router.get("/_give_session_creds")
async def _give_session_creds(request: Request) -> dict[str, Any]:
    """Retrieve session credentials (internal endpoint, not user-facing).

    This endpoint returns the session credentials as JSON.
    It should only be called internally by the gtask_client_impl.

    Returns:
        JSON object containing access token and related credential information.

    Raises:
        HTTPException: If no credentials are found in session.

    """
    credentials_json = request.session.get("credentials")  # type: ignore[attr-defined]

    if not credentials_json:
        raise HTTPException(
            status_code=401,
            detail="No credentials found in session. Please authenticate first.",
        )

    try:
        credentials_data = json.loads(credentials_json)
        return {
            "token": credentials_data.get("token"),
            "refresh_token": credentials_data.get("refresh_token"),
            "token_uri": credentials_data.get("token_uri"),
            "client_id": credentials_data.get("client_id"),
            "client_secret": credentials_data.get("client_secret"),
            "scopes": credentials_data.get("scopes"),
        }
    except (json.JSONDecodeError, KeyError) as e:
        logger.exception("Failed to parse session credentials")
        raise HTTPException(status_code=500, detail=f"Invalid credentials in session: {e!s}") from e
