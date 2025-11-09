"""Stub file for google_auth_oauthlib.flow."""

from typing import Any
from google.oauth2.credentials import Credentials

class Flow:
    """OAuth2 flow for Google authentication."""

    credentials: Credentials

    @classmethod
    def from_client_secrets_file(
        cls,
        client_secrets_file: str,
        scopes: list[str] | None = None,
        redirect_uri: str | None = None,
    ) -> "Flow": ...
    def fetch_token(
        self,
        code: str | None = None,
        state: str | None = None,
    ) -> None: ...
    def authorization_url(
        self,
        access_type: str | None = None,
        prompt: str | None = None,
    ) -> tuple[str, str]: ...

class InstalledAppFlow(Flow):
    """OAuth2 flow for installed applications."""

    @classmethod
    def from_client_secrets_file(
        cls,
        client_secrets_file: str,
        scopes: list[str] | None = None,
        redirect_uri: str | None = None,
    ) -> "InstalledAppFlow": ...
    def run_local_server(
        self,
        port: int = 0,
        authorization_prompt_message: str | None = None,
        success_message: str | None = None,
        open_browser: bool = True,
    ) -> Credentials: ...
