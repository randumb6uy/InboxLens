"""Tests for email ingestion and GmailClient."""

from src.ingestion.client import GmailClient, _parse_sender_details, _parse_email_date
from src.ingestion.fixtures import generate_mock_emails


def test_parse_sender_details():
    full, email, domain = _parse_sender_details("Uber Receipts <receipts.india@uber.com>")
    assert email == "receipts.india@uber.com"
    assert domain == "uber.com"

    _, email_plain, domain_plain = _parse_sender_details("alex@bytebytego.com")
    assert email_plain == "alex@bytebytego.com"
    assert domain_plain == "bytebytego.com"


def test_parse_email_date():
    dt = _parse_email_date("Wed, 23 Sep 2026 14:30:00 +0000")
    assert dt.year == 2026
    assert dt.month == 9
    assert dt.day == 23


def test_generate_mock_emails():
    emails = generate_mock_emails(50)
    assert len(emails) == 50
    assert all(e.id.startswith("msg_") for e in emails)
    assert all(e.sender_email for e in emails)
    assert all(e.subject for e in emails)


def test_gmail_client_mock_fetch():
    client = GmailClient(mock=True)
    emails = client.fetch_recent_emails(limit=100)
    assert len(emails) == 100
    assert emails[0].sender_domain != ""


def test_gmail_client_query_filter():
    client = GmailClient(mock=True)
    uber_emails = client.fetch_recent_emails(limit=100, query="Uber")
    assert len(uber_emails) > 0
    assert all("uber" in e.subject.lower() or "uber" in e.sender.lower() or "uber" in e.body_plain.lower() for e in uber_emails)
