"""Tests for Pydantic data schemas."""

from datetime import date, datetime, timezone
import pytest
from src.schemas import (
    RawEmail,
    ReceiptData,
    MeetingData,
    DeadlineData,
    ExtractedEmail,
)


def test_raw_email_schema():
    email = RawEmail(
        id="msg_123",
        thread_id="th_456",
        sender="Uber <receipts@uber.com>",
        sender_email="receipts@uber.com",
        sender_domain="uber.com",
        subject="Your ride receipt",
        date=datetime.now(timezone.utc),
        snippet="Total: ₹350",
        body_plain="Total: ₹350 on 2026-09-24",
    )
    assert email.id == "msg_123"
    assert email.sender_domain == "uber.com"
    assert email.labels == []


def test_receipt_data_schema():
    receipt = ReceiptData(
        vendor="Swiggy",
        amount=540.50,
        currency="INR",
        date=date(2026, 9, 23),
        category="food",
        is_recurring=False,
    )
    assert receipt.vendor == "Swiggy"
    assert receipt.amount == 540.50
    assert receipt.currency == "INR"


def test_extracted_email_schema():
    extracted = ExtractedEmail(
        email_type="receipt",
        sender_domain="uber.com",
        sender_email="receipts@uber.com",
        urgency="low",
        action_required=False,
        summary="Uber ride receipt for ₹350",
        receipt_data=ReceiptData(
            vendor="Uber",
            amount=350.0,
            category="travel",
        ),
    )
    assert extracted.email_type == "receipt"
    assert extracted.receipt_data is not None
    assert extracted.receipt_data.vendor == "Uber"
