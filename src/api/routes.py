"""FastAPI routes for IndexLens dashboard."""

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.pipeline import run_ingestion_pipeline
from src.storage.db import Database

router = APIRouter(prefix="/api")
db = Database()


class AddVipRequest(BaseModel):
    email: str
    display_name: str = ""
    notes: str = ""


class SyncRequest(BaseModel):
    limit: int = 100
    mock: Optional[bool] = None


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": "IndexLens", "version": "0.1.0"}


@router.get("/stats/overview")
def get_overview() -> dict[str, Any]:
    """Metrics cards and donut chart distribution for Overview tab."""
    metrics = db.get_overview_metrics()
    class_stats = db.get_classification_stats()
    return {
        "metrics": metrics,
        "classification": class_stats,
    }


@router.get("/stats/spend")
def get_spend() -> dict[str, Any]:
    """Spend analytics and transactions for Financial tab."""
    return db.get_spend_analytics()


@router.get("/subscriptions")
def get_subscriptions() -> list[dict[str, Any]]:
    """List detected active subscriptions and renewal dates."""
    return db.list_subscriptions()


@router.get("/newsletters")
def get_newsletters() -> list[dict[str, Any]]:
    """List detected newsletter senders and 1-click unsubscribe links."""
    return db.list_newsletters()


@router.get("/contacts/important")
def get_important_contacts() -> dict[str, Any]:
    """List VIP contacts and correspondence threads."""
    vip_set = db.get_vip_contacts()
    emails = db.list_emails(classification="PERSONAL", limit=50)
    return {
        "vip_contacts": list(vip_set),
        "recent_threads": emails,
    }


@router.post("/contacts/important")
def add_important_contact(req: AddVipRequest) -> dict[str, Any]:
    """Add a sender to the VIP important contacts list."""
    if not req.email or "@" not in req.email:
        raise HTTPException(status_code=400, detail="Invalid email address.")
    db.add_vip_contact(req.email, req.display_name, req.notes)
    return {"status": "success", "email": req.email}


@router.get("/schedule/upcoming")
def get_upcoming_schedule() -> dict[str, Any]:
    """Meetings and deadlines combined for Schedule tab."""
    return db.list_upcoming_schedule()


@router.get("/jobs")
def get_job_pipeline() -> list[dict[str, Any]]:
    """Detected career and recruitment opportunities."""
    return db.list_job_opportunities()


class ExtractRequest(BaseModel):
    limit: int = 100


@router.post("/extract")
def extract_entities(req: ExtractRequest = ExtractRequest()) -> dict[str, Any]:
    """Trigger LLM/heuristic structured entity extraction on stored emails."""
    from src.extraction.pipeline import run_extraction_pipeline
    results = run_extraction_pipeline(limit=req.limit)
    return {"status": "success", "results": results}


@router.post("/inbox/sync")
def sync_inbox(req: SyncRequest = SyncRequest()) -> dict[str, Any]:
    """Trigger email ingestion and return updated classification stats."""
    emails, stats = run_ingestion_pipeline(limit=req.limit, mock=req.mock)
    return {
        "status": "success",
        "ingested_count": len(emails),
        "stats": stats,
    }


@router.get("/emails/{email_id}")
def get_email_details(email_id: str) -> dict[str, Any]:
    """Get full details of a specific email for the slide-over drawer."""
    email_data = db.get_email(email_id)
    if not email_data:
        raise HTTPException(status_code=404, detail="Email not found.")
    return email_data
