"""OAuth2 authentication helper for Gmail API."""

import logging
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from src.config import GMAIL_CREDENTIALS_PATH, GMAIL_SCOPES, GMAIL_TOKEN_PATH

logger = logging.getLogger(__name__)


class GmailAuthError(Exception):
    """Raised when authentication fails or credentials are missing."""
    pass


def get_gmail_credentials(
    credentials_path: Path = GMAIL_CREDENTIALS_PATH,
    token_path: Path = GMAIL_TOKEN_PATH,
    scopes: list[str] = GMAIL_SCOPES,
) -> Credentials:
    """Retrieve or generate valid Gmail OAuth2 credentials.

    Flow:
    1. Loads cached credentials from token_path if available.
    2. Refreshes expired token if a refresh token is present.
    3. If no token or invalid, launches InstalledAppFlow using credentials_path.
    4. Saves the refreshed/new token to token_path for subsequent runs.
    """
    creds: Optional[Credentials] = None

    # 1. Check existing saved token
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), scopes)
        except Exception as e:
            logger.warning("Failed to load existing token from %s: %s", token_path, e)
            creds = None

    # 2. Refresh or trigger initial authorization
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("Refreshing expired Gmail OAuth token...")
                creds.refresh(Request())
            except Exception as e:
                logger.warning("Failed to refresh token: %s. Re-authenticating...", e)
                creds = None

        if not creds:
            if not credentials_path.exists():
                raise GmailAuthError(
                    f"Credentials file '{credentials_path}' not found.\n"
                    "Please download OAuth2 Client Credentials (Desktop App) from "
                    "Google Cloud Console (APIs & Services > Credentials) and place it as "
                    f"'{credentials_path}', or run with MOCK_GMAIL=true for synthetic testing."
                )

            logger.info("Starting local OAuth2 consent flow for Gmail...")
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes)
            creds = flow.run_local_server(port=0)

        # 3. Save authorized token
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())
        logger.info("Saved authorized credentials to %s", token_path)

    return creds
