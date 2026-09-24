"""Ingestion module for Gmail API and email fetching."""

from src.ingestion.auth import get_gmail_credentials, GmailAuthError
from src.ingestion.client import GmailClient
from src.ingestion.fixtures import generate_mock_emails

__all__ = [
    "get_gmail_credentials",
    "GmailAuthError",
    "GmailClient",
    "generate_mock_emails",
]
