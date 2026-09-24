"""Tests for Database and storage operations."""

from datetime import datetime, timezone
import pytest
from src.schemas.email_schemas import RawEmail
from src.storage.db import Database


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test.db"
    return Database(db_file)


def test_upsert_and_get_email(temp_db):
    email = RawEmail(
        id="db_msg_01",
        thread_id="th_01",
        sender="Swiggy <orders@swiggy.in>",
        sender_email="orders@swiggy.in",
        sender_domain="swiggy.in",
        subject="Order Confirmed",
        date=datetime.now(timezone.utc),
        snippet="Your food is on the way",
        body_plain="Total: ₹450",
    )
    temp_db.upsert_email(email, classification="RECEIPT", matched_rule="receipt_domain", confidence=0.95)

    stored = temp_db.get_email("db_msg_01")
    assert stored is not None
    assert stored["id"] == "db_msg_01"
    assert stored["sender_email"] == "orders@swiggy.in"
    assert stored["classification"] == "RECEIPT"
    assert stored["confidence"] == 0.95


def test_classification_stats(temp_db):
    email1 = RawEmail(
        id="msg_1",
        thread_id="th_1",
        sender="Uber <uber@uber.com>",
        sender_email="uber@uber.com",
        sender_domain="uber.com",
        subject="Ride receipt",
        date=datetime.now(timezone.utc),
        snippet="Total: ₹200",
        body_plain="Total: ₹200",
    )
    email2 = RawEmail(
        id="msg_2",
        thread_id="th_2",
        sender="Friend <friend@gmail.com>",
        sender_email="friend@gmail.com",
        sender_domain="gmail.com",
        subject="What's up",
        date=datetime.now(timezone.utc),
        snippet="Hey",
        body_plain="Hey",
    )
    temp_db.upsert_email(email1, classification="RECEIPT")
    temp_db.upsert_email(email2, classification="NEEDS_LLM")

    stats = temp_db.get_classification_stats()
    assert stats["total"] == 2
    assert stats["deterministic_count"] == 1
    assert stats["needs_llm_count"] == 1
    assert stats["deterministic_rate"] == 50.0


def test_vip_contacts(temp_db):
    temp_db.add_vip_contact("ceo@company.com", display_name="CEO", notes="Important")
    contacts = temp_db.get_vip_contacts()
    assert "ceo@company.com" in contacts
