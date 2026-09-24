"""Batch ingestion and classification pipeline."""

import logging
from pathlib import Path
from typing import Any, Optional

from src.classification.router import EmailRouter
from src.ingestion.client import GmailClient
from src.schemas.email_schemas import RawEmail
from src.storage.db import Database, DEFAULT_DB_PATH

logger = logging.getLogger(__name__)


def run_ingestion_pipeline(
    limit: int = 100,
    query: Optional[str] = None,
    mock: Optional[bool] = None,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> tuple[list[RawEmail], dict[str, Any]]:
    """Run batch email ingestion and deterministic classification."""
    db = Database(db_path)
    client = GmailClient(mock=mock)

    vip_contacts = db.get_vip_contacts()
    router = EmailRouter(vip_contacts=vip_contacts)

    logger.info("Fetching up to %d emails...", limit)
    emails = client.fetch_recent_emails(limit=limit, query=query)

    for email in emails:
        try:
            route_res = router.route(email)
            db.upsert_email(
                email=email,
                classification=route_res.category,
                matched_rule=route_res.matched_rule,
                confidence=route_res.confidence,
            )
        except Exception as err:
            logger.error("Failed processing email %s: %s", getattr(email, "id", "unknown"), err)

    stats = db.get_classification_stats()
    return emails, stats
