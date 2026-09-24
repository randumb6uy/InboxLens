"""Comprehensive corner cases, boundary conditions, and break cases test suite."""

import base64
import datetime as dt
from datetime import datetime, timezone
import pytest

from src.classification.router import EmailRouter
from src.ingestion.client import (
    _extract_body_parts,
    _parse_email_date,
    _parse_sender_details,
)
from src.schemas.email_schemas import RawEmail
from src.storage.db import Database


# ==============================================================================
# 1. INGESTION & HEADER PARSING BREAK CASES
# ==============================================================================

def test_parse_sender_details_none():
    """Header is None."""
    full, email_addr, domain = _parse_sender_details(None)
    assert full == ""
    assert email_addr == ""
    assert domain == ""


def test_parse_sender_details_empty():
    """Header is empty string or pure whitespace."""
    full, email_addr, domain = _parse_sender_details("   ")
    assert email_addr == ""
    assert domain == ""


def test_parse_sender_details_no_at_symbol():
    """Header lacks '@' (e.g., local system user)."""
    full, email_addr, domain = _parse_sender_details("mailer-daemon")
    assert email_addr == "mailer-daemon"
    assert domain == ""


def test_parse_sender_details_complex_characters():
    """Header contains emojis, quotes, and commas."""
    header = '🚀 "Sharma, Ramesh (CEO)" <ramesh.sharma+filter@corp.example.co.in>'
    full, email_addr, domain = _parse_sender_details(header)
    assert email_addr == "ramesh.sharma+filter@corp.example.co.in"
    assert domain == "corp.example.co.in"


def test_parse_email_date_corrupted():
    """Date header is completely corrupted or invalid string."""
    corrupted_inputs = [
        "",
        "None",
        "Tomorrow morning",
        "2026-99-99 25:99:99",
        "Wed, 32 Sep 2026 12:00:00 +0000",
    ]
    for date_str in corrupted_inputs:
        parsed = _parse_email_date(date_str)
        assert isinstance(parsed, datetime)
        assert parsed.tzinfo is not None  # Must always be timezone-aware


def test_parse_email_date_missing_timezone():
    """Date without explicit timezone info should default to UTC."""
    date_str = "Wed, 23 Sep 2026 14:30:00"
    parsed = _parse_email_date(date_str)
    assert parsed.tzinfo == timezone.utc


# ==============================================================================
# 2. PAYLOAD & BASE64 DECODING BREAK CASES
# ==============================================================================

def test_extract_body_parts_missing_base64_padding():
    """Base64 data with stripped padding (common in raw Gmail API payloads)."""
    raw_text = "Your invoice total is ₹500"
    # Encode and intentionally strip trailing '='
    encoded = base64.urlsafe_b64encode(raw_text.encode("utf-8")).decode("ascii").rstrip("=")
    payload = {
        "mimeType": "text/plain",
        "body": {"data": encoded},
    }
    plain, html = _extract_body_parts(payload)
    assert "Your invoice total is ₹500" in plain


def test_extract_body_parts_empty_and_null_payload():
    """Payload has empty body or null parts."""
    payload = {
        "mimeType": "multipart/mixed",
        "body": {},
        "parts": None,
    }
    plain, html = _extract_body_parts(payload)
    assert plain == ""
    assert html is None


def test_extract_body_parts_deeply_nested_multipart():
    """Complex 3-level nested multipart MIME structure."""
    text_content = "Plain text body content"
    html_content = "<p>HTML body content</p>"

    b64_text = base64.urlsafe_b64encode(text_content.encode("utf-8")).decode("ascii")
    b64_html = base64.urlsafe_b64encode(html_content.encode("utf-8")).decode("ascii")

    nested_payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": b64_text}},
                    {"mimeType": "text/html", "body": {"data": b64_html}},
                ],
            }
        ],
    }
    plain, html = _extract_body_parts(nested_payload)
    assert plain == text_content
    assert html == html_content


def test_extract_body_parts_extremely_large_payload():
    """Massive 200KB plain text payload."""
    large_text = "IndexLens log line\n" * 10000
    b64_large = base64.urlsafe_b64encode(large_text.encode("utf-8")).decode("ascii")
    payload = {
        "mimeType": "text/plain",
        "body": {"data": b64_large},
    }
    plain, _ = _extract_body_parts(payload)
    assert len(plain) == len(large_text.strip())


# ==============================================================================
# 3. ROUTER & CLASSIFICATION CORNER CASES
# ==============================================================================

def test_router_vip_case_insensitivity():
    """VIP contacts defined with mixed case should match lowercase sender."""
    router = EmailRouter(vip_contacts={"INVESTOR@CapitalVentures.COM"})
    email = RawEmail(
        id="vip_01",
        thread_id="th_vip_01",
        sender="Investor <investor@capitalventures.com>",
        sender_email="investor@capitalventures.com",
        sender_domain="capitalventures.com",
        subject="Term Sheet Follow-up",
        date=datetime.now(timezone.utc),
        body_plain="Please review the signed docs.",
    )
    res = router.route(email)
    assert res.category == "PERSONAL"
    assert res.matched_rule == "vip_sender_match"


def test_router_currency_variations():
    """Receipt matching on different Indian and global currency formats."""
    currencies = [
        "Total: INR 1,450.00",
        "Total: Rs. 990",
        "Total: Rs 450",
        "Total: $45.00",
        "Total: €39.50",
        "Total: £25.00",
        "Total: ₹1,299",
    ]
    router = EmailRouter()
    for curr in currencies:
        email = RawEmail(
            id=f"curr_{hash(curr)}",
            thread_id="th_curr",
            sender="Custom Vendor <billing@vendor.in>",
            sender_email="billing@vendor.in",
            sender_domain="vendor.in",
            subject="Invoice for services rendered",
            date=datetime.now(timezone.utc),
            body_plain=f"Thank you for your business.\n{curr}\nPaid via Card.",
        )
        res = router.route(email)
        assert res.category == "RECEIPT", f"Failed for currency string: {curr}"


def test_router_conflicting_signals_promo_vs_receipt():
    """Promotional email from a receipt domain (e.g. Amazon sale promo)."""
    router = EmailRouter()
    promo_email = RawEmail(
        id="promo_conflict",
        thread_id="th_conf",
        sender="Amazon.in <deals@amazon.in>",
        sender_email="deals@amazon.in",
        sender_domain="amazon.in",
        subject="Great Indian Festival: Flat 50% OFF on Electronics!",
        date=datetime.now(timezone.utc),
        body_plain="Hurry up and shop the mega sale before it ends.",
    )
    res = router.route(promo_email)
    assert res.category == "PROMOTIONAL"


def test_router_empty_subject_and_body():
    """Email with empty subject and empty body."""
    router = EmailRouter()
    email = RawEmail(
        id="empty_msg",
        thread_id="th_empty",
        sender="Unknown <unknown@example.com>",
        sender_email="unknown@example.com",
        sender_domain="example.com",
        subject="",
        date=datetime.now(timezone.utc),
        body_plain="",
    )
    res = router.route(email)
    assert res.category == "NEEDS_LLM"
    assert res.matched_rule == "no_deterministic_rule_matched"


def test_router_emojis_and_multilingual_content():
    """Subject and body with emojis and Hindi text."""
    router = EmailRouter()
    email = RawEmail(
        id="hindi_msg",
        thread_id="th_hindi",
        sender="Swiggy <orders@swiggy.in>",
        sender_email="orders@swiggy.in",
        sender_domain="swiggy.in",
        subject="🎉 आपका ऑर्डर डिलीवर हो गया: Order Delivered!",
        date=datetime.now(timezone.utc),
        body_plain="Total: ₹540.00\nधन्यवाद!",
    )
    res = router.route(email)
    assert res.category == "RECEIPT"


# ==============================================================================
# 4. DATABASE & STORAGE CORNER CASES
# ==============================================================================

@pytest.fixture
def temp_db(tmp_path):
    return Database(tmp_path / "corner_cases.db")


def test_db_sql_injection_resilience(temp_db):
    """Malicious SQL injection payloads in all string fields."""
    sql_payload = "'; DROP TABLE emails; DROP TABLE receipts; --"
    email = RawEmail(
        id=sql_payload,
        thread_id=sql_payload,
        sender=f"Attacker <{sql_payload}@exploit.com>",
        sender_email=f"hacker@{sql_payload}.org",
        sender_domain="exploit.com",
        subject=sql_payload,
        date=datetime.now(timezone.utc),
        snippet=sql_payload,
        body_plain=sql_payload,
    )
    # Must not throw and must not drop tables
    temp_db.upsert_email(email, classification="NEEDS_LLM", matched_rule=sql_payload)

    retrieved = temp_db.get_email(sql_payload)
    assert retrieved is not None
    assert retrieved["subject"] == sql_payload

    # Verify table integrity
    stats = temp_db.get_classification_stats()
    assert stats["total"] == 1


def test_db_upsert_idempotency(temp_db):
    """Upserting the same message ID repeatedly updates metadata without duplicate rows."""
    email = RawEmail(
        id="idem_msg_01",
        thread_id="th_idem",
        sender="Uber <receipts@uber.com>",
        sender_email="receipts@uber.com",
        sender_domain="uber.com",
        subject="Uber Receipt",
        date=datetime.now(timezone.utc),
        body_plain="Total: ₹250",
    )
    temp_db.upsert_email(email, classification="NEEDS_LLM", matched_rule="first_pass", confidence=0.5)
    temp_db.upsert_email(email, classification="RECEIPT", matched_rule="refined_pass", confidence=0.95)

    assert temp_db.get_classification_stats()["total"] == 1
    updated = temp_db.get_email("idem_msg_01")
    assert updated["classification"] == "RECEIPT"
    assert updated["matched_rule"] == "refined_pass"
    assert updated["confidence"] == 0.95


def test_db_pagination_boundary_cases(temp_db):
    """Listing emails with offset greater than count or negative limits."""
    email = RawEmail(
        id="msg_pg",
        thread_id="th_pg",
        sender="Test <test@test.com>",
        sender_email="test@test.com",
        sender_domain="test.com",
        subject="Hello",
        date=datetime.now(timezone.utc),
        body_plain="Body",
    )
    temp_db.upsert_email(email, classification="PERSONAL")

    assert len(temp_db.list_emails(offset=100)) == 0
    assert len(temp_db.list_emails(classification="RECEIPT")) == 0
    assert len(temp_db.list_emails(classification="PERSONAL", limit=10)) == 1


def test_db_empty_state_stats(temp_db):
    """Statistics when database is completely empty."""
    stats = temp_db.get_classification_stats()
    assert stats["total"] == 0
    assert stats["breakdown"] == {}
    assert stats["deterministic_rate"] == 0.0


def test_db_vip_duplicate_handling(temp_db):
    """Adding the same VIP contact multiple times updates display name cleanly."""
    temp_db.add_vip_contact("partner@vc.com", display_name="Partner V1")
    temp_db.add_vip_contact("partner@vc.com", display_name="Partner V2", notes="Promoted")

    contacts = temp_db.get_vip_contacts()
    assert len(contacts) == 1
    assert "partner@vc.com" in contacts
