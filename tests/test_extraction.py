"""Tests for Phase 2: LLM extraction pipeline, semantic cache, and schema validation."""

import datetime as dt
from pathlib import Path
import pytest

from src.extraction.cache import ExtractionCache
from src.extraction.extractor import LLMExtractor
from src.extraction.pipeline import run_extraction_pipeline
from src.schemas.email_schemas import RawEmail
from src.storage.db import Database


@pytest.fixture
def temp_cache_file(tmp_path: Path) -> Path:
    return tmp_path / "test_cache.json"


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_extract.db"


@pytest.fixture
def sample_receipt_email() -> RawEmail:
    return RawEmail(
        id="msg_swiggy_123",
        thread_id="th_123",
        sender="Swiggy <orders@swiggy.in>",
        sender_email="orders@swiggy.in",
        sender_domain="swiggy.in",
        subject="Your order from Burger King has been delivered",
        date=dt.datetime(2026, 9, 20, 19, 45, tzinfo=dt.timezone.utc),
        snippet="Total paid: ₹485.50 via UPI. Thank you for ordering on Swiggy.",
        body_plain="Order Details: Whopper Meal x 1. Item total: ₹450. Taxes: ₹35.50. Total amount: ₹485.50. Payment mode: Google Pay UPI.",
        labels=["INBOX", "RECEIPTS"],
    )


@pytest.fixture
def sample_subscription_email() -> RawEmail:
    return RawEmail(
        id="msg_netflix_456",
        thread_id="th_456",
        sender="Netflix <info@mailer.netflix.com>",
        sender_email="info@mailer.netflix.com",
        sender_domain="netflix.com",
        subject="Your monthly Netflix subscription invoice",
        date=dt.datetime(2026, 9, 18, 10, 0, tzinfo=dt.timezone.utc),
        snippet="Your membership has renewed for ₹649. Next billing cycle: Oct 18, 2026.",
        body_plain="Hi Tushar, thanks for your recurring membership. Plan: Premium 4K. Amount: ₹649.00 billed monthly to card ending in 4021.",
        labels=["INBOX"],
    )


@pytest.fixture
def sample_meeting_email() -> RawEmail:
    return RawEmail(
        id="msg_meet_789",
        thread_id="th_789",
        sender="Alex Chen <alex@techcorp.io>",
        sender_email="alex@techcorp.io",
        sender_domain="techcorp.io",
        subject="Invitation: IndexLens System Architecture Review @ Fri Sep 26, 2026",
        date=dt.datetime(2026, 9, 21, 14, 0, tzinfo=dt.timezone.utc),
        snippet="Join Google Meet at https://meet.google.com/abc-defg-hij",
        body_plain="Please join the architecture review discussion.\nGoogle Meet: https://meet.google.com/abc-defg-hij\nAgenda: review DB schemas and API design.",
        labels=["INBOX"],
    )


@pytest.fixture
def sample_deadline_email() -> RawEmail:
    return RawEmail(
        id="msg_bill_101",
        thread_id="th_101",
        sender="Airtel Broadband <ebill@airtel.com>",
        sender_email="ebill@airtel.com",
        sender_domain="airtel.com",
        subject="Your Airtel Fiber Bill: Due by Sep 28, 2026",
        date=dt.datetime(2026, 9, 15, 8, 30, tzinfo=dt.timezone.utc),
        snippet="Dear Customer, your bill of ₹943.00 is due by Sep 28, 2026. Avoid late fee.",
        body_plain="Bill summary for 9876543210. Plan: Entertainment 200Mbps. Bill Amount: ₹943.00. Payment due by Sep 28, 2026.",
        labels=["INBOX"],
    )


class TestExtractionCache:
    def test_cache_key_generation(self) -> None:
        key1 = ExtractionCache.generate_cache_key(
            sender_domain="uber.com",
            subject="Your trip on Sep 14, 2026",
            body_sample="Total: ₹350 on trip ID 981729",
        )
        key2 = ExtractionCache.generate_cache_key(
            sender_domain="uber.com",
            subject="Your trip on Oct 02, 2026",
            body_sample="Total: ₹420 on trip ID 441029",
        )
        # Because date/digits are normalized to template tokens, the keys should match identical receipt templates
        assert key1 == key2

    def test_cache_set_and_persistence(self, temp_cache_file: Path) -> None:
        cache = ExtractionCache(cache_file=temp_cache_file)
        assert len(cache) == 0

        cache.set("k1", {"vendor": "Swiggy", "amount": 485.5})
        assert cache.has("k1")
        assert cache.get("k1") == {"vendor": "Swiggy", "amount": 485.5}
        assert len(cache) == 1

        # Check persistence by reloading from disk
        cache2 = ExtractionCache(cache_file=temp_cache_file)
        assert cache2.has("k1")
        assert cache2.get("k1")["vendor"] == "Swiggy"

    def test_cache_clear(self, temp_cache_file: Path) -> None:
        cache = ExtractionCache(cache_file=temp_cache_file)
        cache.set("k1", {"foo": "bar"})
        assert cache.has("k1")
        cache.clear()
        assert len(cache) == 0
        assert not cache.has("k1")


class TestLLMExtractor:
    def test_extract_receipt(self, sample_receipt_email: RawEmail, temp_cache_file: Path) -> None:
        cache = ExtractionCache(cache_file=temp_cache_file)
        extractor = LLMExtractor(api_key="", cache=cache)

        receipt = extractor.extract_receipt(sample_receipt_email)
        assert receipt.vendor in ("Swiggy", "Burger King")
        assert receipt.amount == 485.50
        assert receipt.currency == "INR"
        assert receipt.category == "food"
        assert not receipt.is_recurring

    def test_extract_subscription(self, sample_subscription_email: RawEmail, temp_cache_file: Path) -> None:
        cache = ExtractionCache(cache_file=temp_cache_file)
        extractor = LLMExtractor(api_key="", cache=cache)

        receipt = extractor.extract_receipt(sample_subscription_email)
        assert receipt.vendor == "Netflix"
        assert receipt.amount == 649.0
        assert receipt.category == "subscription"
        assert receipt.is_recurring is True

    def test_extract_meeting(self, sample_meeting_email: RawEmail, temp_cache_file: Path) -> None:
        cache = ExtractionCache(cache_file=temp_cache_file)
        extractor = LLMExtractor(api_key="", cache=cache)

        meeting = extractor.extract_meeting(sample_meeting_email)
        assert "IndexLens System Architecture Review" in meeting.title
        assert meeting.location_or_link == "https://meet.google.com/abc-defg-hij"
        assert "alex" in meeting.organizer.lower()

    def test_extract_deadline(self, sample_deadline_email: RawEmail, temp_cache_file: Path) -> None:
        cache = ExtractionCache(cache_file=temp_cache_file)
        extractor = LLMExtractor(api_key="", cache=cache)

        deadline = extractor.extract_deadline(sample_deadline_email)
        assert "Airtel" in deadline.description or "due" in deadline.description.lower()
        assert deadline.due_date is not None
        assert deadline.source_context != ""

    def test_cache_hit_prevents_reprocessing(self, sample_receipt_email: RawEmail, temp_cache_file: Path) -> None:
        cache = ExtractionCache(cache_file=temp_cache_file)
        extractor = LLMExtractor(api_key="", cache=cache)

        # First extraction: writes to cache
        res1 = extractor.extract(sample_receipt_email)
        assert len(cache) == 1

        # Second extraction: hits cache
        res2 = extractor.extract(sample_receipt_email)
        assert res1.summary == res2.summary
        assert res1.receipt_data.amount == res2.receipt_data.amount


class TestExtractionPipeline:
    def test_run_extraction_pipeline(self, temp_db_path: Path, temp_cache_file: Path, sample_receipt_email: RawEmail, sample_subscription_email: RawEmail, sample_meeting_email: RawEmail) -> None:
        db = Database(temp_db_path)
        cache = ExtractionCache(temp_cache_file)
        extractor = LLMExtractor(api_key="", cache=cache)

        # Ingest raw emails into DB
        db.upsert_email(sample_receipt_email, classification="RECEIPT")
        db.upsert_email(sample_subscription_email, classification="RECEIPT")
        db.upsert_email(sample_meeting_email, classification="MEETING")

        # Run extraction pipeline
        results = run_extraction_pipeline(limit=10, db_path=temp_db_path, extractor=extractor)

        assert results["processed_count"] == 3
        assert results["receipts_extracted"] == 2
        assert results["subscriptions_detected"] == 1  # Netflix is recurring
        assert results["meetings_extracted"] == 1

        # Check DB receipts
        with db.get_connection() as conn:
            receipts = conn.execute("SELECT * FROM receipts").fetchall()
            assert len(receipts) == 2

            subs = conn.execute("SELECT * FROM subscriptions").fetchall()
            assert len(subs) == 1
            assert subs[0]["vendor"] == "Netflix"
            assert subs[0]["last_amount"] == 649.0

            meets = conn.execute("SELECT * FROM meetings").fetchall()
            assert len(meets) == 1
            assert "Architecture Review" in meets[0]["title"]

        # Run pipeline again: since child tables are now populated, processed count should be 0 (no duplicate work)
        results2 = run_extraction_pipeline(limit=10, db_path=temp_db_path, extractor=extractor)
        assert results2["processed_count"] == 0
