"""Pydantic schemas for raw and extracted email data."""

import datetime as dt
from typing import Literal, Optional
from pydantic import BaseModel, Field


class RawEmail(BaseModel):
    """Raw parsed email ingested from Gmail API."""
    id: str = Field(..., description="Gmail message ID")
    thread_id: str = Field(..., description="Gmail thread ID")
    sender: str = Field(..., description="Full 'From' header")
    sender_email: str = Field(..., description="Extracted sender email address")
    sender_domain: str = Field(..., description="Domain of sender (e.g. uber.com)")
    recipient: Optional[str] = Field(None, description="To header")
    subject: str = Field("", description="Email subject line")
    date: dt.datetime = Field(..., description="Email timestamp")
    snippet: str = Field("", description="Gmail short snippet preview")
    body_plain: str = Field("", description="Plain text body content")
    body_html: Optional[str] = Field(None, description="Raw HTML content if present")
    labels: list[str] = Field(default_factory=list, description="Gmail labels (INBOX, UNREAD, etc.)")


class ReceiptData(BaseModel):
    """Extracted financial receipt or billing transaction."""
    vendor: str
    amount: Optional[float] = None
    currency: str = "INR"
    date: Optional[dt.date] = None
    category: str = "other"  # e.g. "food", "subscription", "travel", "utilities", "shopping"
    is_recurring: Optional[bool] = None  # heuristic flag for subscription detection


class MeetingData(BaseModel):
    """Extracted calendar invite or scheduled meeting."""
    title: str
    datetime_start: Optional[dt.datetime] = None
    location_or_link: Optional[str] = None
    organizer: Optional[str] = None


class DeadlineData(BaseModel):
    """Extracted action item, bill due date, or submission deadline."""
    description: str
    due_date: Optional[dt.date] = None
    source_context: str = ""  # short excerpt giving context


class ExtractedEmail(BaseModel):
    """Fully structured output for classified and extracted emails."""
    email_type: Literal[
        "receipt",
        "personal",
        "job_related",
        "travel",
        "bill",
        "meeting_invite",
        "deadline",
        "newsletter",
        "promotional",
        "other",
    ]
    sender_domain: str
    sender_email: str
    is_vip_sender: bool = False  # matched against user-defined important-contacts list
    urgency: Literal["low", "medium", "high"] = "low"
    action_required: bool = False
    summary: str = Field(..., description="One sentence summary")
    receipt_data: Optional[ReceiptData] = None
    meeting_data: Optional[MeetingData] = None
    deadline_data: Optional[DeadlineData] = None
