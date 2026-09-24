"""Tests for deterministic EmailRouter."""

from datetime import datetime, timezone
from src.classification.router import EmailRouter
from src.schemas.email_schemas import RawEmail


def test_router_receipt_classification():
    router = EmailRouter()
    email = RawEmail(
        id="test_1",
        thread_id="th_1",
        sender="Uber Receipts <receipts.india@uber.com>",
        sender_email="receipts.india@uber.com",
        sender_domain="uber.com",
        subject="Your ride with Uber",
        date=datetime.now(timezone.utc),
        snippet="Total: ₹350.00",
        body_plain="Total: ₹350.00 on 2026-09-24",
    )
    res = router.route(email)
    assert res.category == "RECEIPT"
    assert res.confidence >= 0.90


def test_router_newsletter_classification():
    router = EmailRouter()
    email = RawEmail(
        id="test_2",
        thread_id="th_2",
        sender="TLDR <dan@tldr.tech>",
        sender_email="dan@tldr.tech",
        sender_domain="tldr.tech",
        subject="TLDR Daily Tech",
        date=datetime.now(timezone.utc),
        snippet="Headlines today",
        body_plain="Headlines\nTo unsubscribe click here.",
    )
    res = router.route(email)
    assert res.category == "NEWSLETTER"


def test_router_vip_contact():
    router = EmailRouter(vip_contacts={"boss@company.com"})
    email = RawEmail(
        id="test_3",
        thread_id="th_3",
        sender="Boss <boss@company.com>",
        sender_email="boss@company.com",
        sender_domain="company.com",
        subject="Urgent Project Sync",
        date=datetime.now(timezone.utc),
        snippet="Need your update",
        body_plain="Need your update by tomorrow.",
    )
    res = router.route(email)
    assert res.category == "PERSONAL"
    assert res.matched_rule == "vip_sender_match"


def test_router_ambiguous_fallback():
    router = EmailRouter()
    email = RawEmail(
        id="test_4",
        thread_id="th_4",
        sender="Random Person <random@stranger.org>",
        sender_email="random@stranger.org",
        sender_domain="stranger.org",
        subject="Hello there friend",
        date=datetime.now(timezone.utc),
        snippet="Can we chat?",
        body_plain="Wanted to ask you a question.",
    )
    res = router.route(email)
    assert res.category == "NEEDS_LLM"
