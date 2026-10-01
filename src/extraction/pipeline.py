"""Batch extraction pipeline orchestrator."""

import logging
from pathlib import Path
from typing import Any, Optional

from src.extraction.extractor import LLMExtractor
from src.schemas.email_schemas import RawEmail
from src.storage.db import DEFAULT_DB_PATH, Database

logger = logging.getLogger(__name__)


def run_extraction_pipeline(
    limit: int = 100,
    db_path: Path | str = DEFAULT_DB_PATH,
    extractor: Optional[LLMExtractor] = None,
) -> dict[str, Any]:
    """Extract structured entities (receipts, subscriptions, meetings, deadlines) from unextracted emails."""
    db = Database(db_path)
    if extractor is None:
        extractor = LLMExtractor()

    unextracted = db.get_unextracted_emails(limit=limit)
    logger.info("Found %d unextracted emails to process", len(unextracted))

    receipts_count = 0
    subs_count = 0
    meetings_count = 0
    deadlines_count = 0

    for email in unextracted:
        try:
            # Query existing email classification for hint
            stored = db.get_email(email.id)
            classification = stored["classification"] if stored else None

            extracted = extractor.extract(email, classification_hint=classification)

            # 1. Process Receipt
            if extracted.receipt_data and extracted.receipt_data.amount is not None:
                r = extracted.receipt_data
                r_date_str = r.date.isoformat() if r.date else email.date.strftime("%Y-%m-%d")
                db.insert_receipt(
                    email_id=email.id,
                    vendor=r.vendor,
                    amount=r.amount,
                    currency=r.currency,
                    date=r_date_str,
                    category=r.category,
                    is_recurring=bool(r.is_recurring),
                )
                receipts_count += 1

                # If recurring, upsert into subscriptions
                if r.is_recurring:
                    db.insert_subscription(
                        vendor=r.vendor,
                        cadence="monthly",
                        last_amount=r.amount,
                        currency=r.currency,
                        last_charge_date=r_date_str,
                        next_expected_date=r_date_str,  # heuristic next cycle
                        status="active",
                    )
                    subs_count += 1

            # 2. Process Meeting
            if extracted.meeting_data and extracted.meeting_data.title:
                m = extracted.meeting_data
                start_iso = m.datetime_start.isoformat() if m.datetime_start else email.date.isoformat()
                db.insert_meeting(
                    email_id=email.id,
                    title=m.title,
                    datetime_start=start_iso,
                    location_or_link=m.location_or_link or "",
                    organizer=m.organizer or email.sender,
                )
                meetings_count += 1

            # 3. Process Deadline
            if extracted.deadline_data and extracted.deadline_data.description:
                d = extracted.deadline_data
                due_str = d.due_date.isoformat() if d.due_date else ""
                db.insert_deadline(
                    email_id=email.id,
                    description=d.description,
                    due_date=due_str,
                    source_context=d.source_context or email.snippet,
                )
                deadlines_count += 1

        except Exception as err:
            logger.error("Error extracting email %s: %s", email.id, err)

    results = {
        "processed_count": len(unextracted),
        "receipts_extracted": receipts_count,
        "subscriptions_detected": subs_count,
        "meetings_extracted": meetings_count,
        "deadlines_extracted": deadlines_count,
    }
    logger.info("Extraction complete: %s", results)
    return results
