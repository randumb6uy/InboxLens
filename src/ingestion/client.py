"""Gmail API client for fetching and parsing raw emails."""

import base64
import email.utils
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from googleapiclient.discovery import Resource, build

from src.config import GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH, MOCK_GMAIL
from src.ingestion.auth import get_gmail_credentials
from src.ingestion.fixtures import generate_mock_emails
from src.schemas.email_schemas import RawEmail

logger = logging.getLogger(__name__)


def _extract_body_parts(payload: dict[str, Any]) -> tuple[str, Optional[str]]:
    """Recursively traverse message payload to extract plain text and HTML content."""
    plain_text = ""
    html_text: Optional[str] = None

    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if body_data:
        try:
            # Gmail uses URL-safe base64 encoding without padding
            decoded = base64.urlsafe_b64decode(body_data.encode("ASCII")).decode("utf-8", errors="replace")
            if "text/plain" in mime_type:
                plain_text += decoded
            elif "text/html" in mime_type:
                html_text = decoded
        except Exception as e:
            logger.debug("Failed decoding body payload: %s", e)

    # Check multipart children
    for part in payload.get("parts", []):
        sub_plain, sub_html = _extract_body_parts(part)
        if sub_plain:
            plain_text += ("\n" + sub_plain) if plain_text else sub_plain
        if sub_html and not html_text:
            html_text = sub_html

    return plain_text.strip(), html_text


def _parse_sender_details(from_header: str) -> tuple[str, str, str]:
    """Parse 'From: Display Name <user@example.com>' into (full, email, domain)."""
    display_name, email_address = email.utils.parseaddr(from_header)
    clean_email = email_address.lower().strip()
    domain = clean_email.split("@")[-1] if "@" in clean_email else ""
    return from_header, clean_email, domain


def _parse_email_date(date_header: str) -> datetime:
    """Parse RFC 2822 date header into timezone-aware datetime."""
    try:
        parsed = email.utils.parsedate_to_datetime(date_header)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return datetime.now(timezone.utc)


class GmailClient:
    """Client for interacting with Gmail API or mock email fixtures."""

    def __init__(self, mock: Optional[bool] = None):
        # Explicit mock parameter overrides environment
        self.mock = MOCK_GMAIL if mock is None else mock
        self._service: Optional[Resource] = None

        if not self.mock:
            # If credentials don't exist, log and fall back to mock
            if not GMAIL_CREDENTIALS_PATH.exists() and not GMAIL_TOKEN_PATH.exists():
                logger.info(
                    "No Gmail credentials found at %s. Falling back to mock dataset.",
                    GMAIL_CREDENTIALS_PATH,
                )
                self.mock = True
            else:
                try:
                    creds = get_gmail_credentials()
                    self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)
                    logger.info("Connected to live Gmail API service.")
                except Exception as e:
                    logger.warning("Failed connecting to Gmail API (%s). Falling back to mock.", e)
                    self.mock = True

    def list_message_ids(
        self,
        max_results: int = 100,
        query: Optional[str] = None,
        page_token: Optional[str] = None,
    ) -> tuple[list[str], Optional[str]]:
        """List Gmail message IDs matching query."""
        if self.mock:
            mock_emails = generate_mock_emails(max_results)
            return [e.id for e in mock_emails], None

        assert self._service is not None
        req = self._service.users().messages().list(
            userId="me",
            maxResults=min(max_results, 500),
            q=query or "",
            pageToken=page_token,
        )
        resp = req.execute()
        messages = resp.get("messages", [])
        next_token = resp.get("nextPageToken")
        return [m["id"] for m in messages], next_token

    def get_message(self, message_id: str) -> RawEmail:
        """Fetch and parse full message details for a single message ID."""
        if self.mock:
            # Retrieve from mock generator
            mock_emails = generate_mock_emails(100)
            for m in mock_emails:
                if m.id == message_id:
                    return m
            # If not found, return first mock
            return mock_emails[0]

        assert self._service is not None
        msg = (
            self._service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

        headers_list = msg.get("payload", {}).get("headers", [])
        headers_map = {h["name"].lower(): h["value"] for h in headers_list}

        from_header = headers_map.get("from", "Unknown Sender")
        full_sender, sender_email, sender_domain = _parse_sender_details(from_header)
        to_header = headers_map.get("to")
        subject = headers_map.get("subject", "(No Subject)")
        date_str = headers_map.get("date", "")
        email_date = _parse_email_date(date_str)

        body_plain, body_html = _extract_body_parts(msg.get("payload", {}))
        snippet = msg.get("snippet", "")

        return RawEmail(
            id=msg["id"],
            thread_id=msg.get("threadId", msg["id"]),
            sender=full_sender,
            sender_email=sender_email,
            sender_domain=sender_domain,
            recipient=to_header,
            subject=subject,
            date=email_date,
            snippet=snippet,
            body_plain=body_plain or snippet,
            body_html=body_html,
            labels=msg.get("labelIds", []),
        )

    def fetch_recent_emails(
        self,
        limit: int = 100,
        query: Optional[str] = None,
    ) -> list[RawEmail]:
        """Fetch up to `limit` raw emails (live or synthetic)."""
        if self.mock:
            emails = generate_mock_emails(limit)
            if query:
                q_lower = query.lower()
                emails = [
                    e for e in emails
                    if q_lower in e.subject.lower() or q_lower in e.body_plain.lower() or q_lower in e.sender.lower()
                ]
            return emails[:limit]

        results: list[RawEmail] = []
        page_token: Optional[str] = None

        while len(results) < limit:
            batch_size = min(limit - len(results), 100)
            msg_ids, page_token = self.list_message_ids(
                max_results=batch_size,
                query=query,
                page_token=page_token,
            )
            if not msg_ids:
                break

            for msg_id in msg_ids:
                try:
                    email_item = self.get_message(msg_id)
                    results.append(email_item)
                    if len(results) >= limit:
                        break
                except Exception as err:
                    logger.error("Failed fetching message %s: %s", msg_id, err)

            if not page_token:
                break

        return results
