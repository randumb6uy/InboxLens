"""Tiered LLM extraction pipeline using OpenRouter and Instructor with heuristic fallbacks."""

import datetime as dt
import logging
import re
from typing import Any, Optional

from src.config import (
    ANOMALY_MODEL,
    EXTRACTION_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
)
from src.extraction.cache import ExtractionCache
from src.schemas.email_schemas import (
    DeadlineData,
    ExtractedEmail,
    MeetingData,
    RawEmail,
    ReceiptData,
)

logger = logging.getLogger(__name__)


class LLMExtractor:
    """Extracts structured entities from unstructured email bodies.
    
    Uses OpenRouter with Instructor for schema validation, with automatic
    semantic caching and deterministic heuristic fallbacks for offline testing.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        cache: Optional[ExtractionCache] = None,
    ):
        self.api_key = api_key if api_key is not None else OPENROUTER_API_KEY
        self.base_url = base_url or OPENROUTER_BASE_URL
        self.model = model or EXTRACTION_MODEL
        self.anomaly_model = ANOMALY_MODEL
        self.cache = cache if cache is not None else ExtractionCache()

        self._client: Any = None
        self._is_live = False
        self._init_client()

    def _init_client(self) -> None:
        """Initialize instructor client if valid API key is present."""
        if (
            self.api_key
            and self.api_key.strip()
            and self.api_key != "your_openrouter_api_key_here"
            and not self.api_key.lower().startswith("mock")
        ):
            try:
                import instructor
                from openai import OpenAI

                raw_client = OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    default_headers={
                        "HTTP-Referer": "https://github.com/indexlens/indexlens",
                        "X-Title": "IndexLens",
                    },
                )
                self._client = instructor.from_openai(raw_client, mode=instructor.Mode.JSON)
                self._is_live = True
                logger.info("OpenRouter LLM extractor initialized with model '%s'", self.model)
            except Exception as err:
                logger.warning("Could not initialize OpenRouter client (%s). Using heuristic extraction.", err)
                self._is_live = False
        else:
            logger.info("No OpenRouter API key found. Using heuristic extraction fallback.")
            self._is_live = False

    @property
    def is_live(self) -> bool:
        return self._is_live

    def extract(
        self,
        email: RawEmail,
        classification_hint: Optional[str] = None,
        use_cache: bool = True,
    ) -> ExtractedEmail:
        """Extract full structured information from a raw email."""
        cache_key = ExtractionCache.generate_cache_key(
            sender_domain=email.sender_domain,
            subject=email.subject,
            body_sample=email.body_plain,
        )

        if use_cache and self.cache.has(cache_key):
            cached_data = self.cache.get(cache_key)
            if cached_data:
                try:
                    return ExtractedEmail.model_validate(cached_data)
                except Exception as err:
                    logger.debug("Failed validating cached item %s: %s", cache_key, err)

        # Attempt live LLM extraction if client is active
        if self._is_live and self._client:
            try:
                extracted = self._extract_llm(email, classification_hint)
                if use_cache:
                    self.cache.set(cache_key, extracted.model_dump(mode="json"))
                return extracted
            except Exception as err:
                logger.warning(
                    "LLM extraction failed for email %s: %s. Falling back to heuristic extraction.",
                    email.id,
                    err,
                )

        # Heuristic extraction fallback
        extracted = self._extract_heuristic(email, classification_hint)
        if use_cache:
            self.cache.set(cache_key, extracted.model_dump(mode="json"))
        return extracted

    def extract_receipt(self, email: RawEmail) -> ReceiptData:
        """Extract structured receipt details."""
        extracted = self.extract(email, classification_hint="RECEIPT")
        if extracted.receipt_data:
            return extracted.receipt_data
        return self._heuristic_receipt(email)

    def extract_meeting(self, email: RawEmail) -> MeetingData:
        """Extract structured calendar/meeting details."""
        extracted = self.extract(email, classification_hint="MEETING")
        if extracted.meeting_data:
            return extracted.meeting_data
        return self._heuristic_meeting(email)

    def extract_deadline(self, email: RawEmail) -> DeadlineData:
        """Extract structured deadline details."""
        extracted = self.extract(email, classification_hint="DEADLINE")
        if extracted.deadline_data:
            return extracted.deadline_data
        return self._heuristic_deadline(email)

    def _extract_llm(self, email: RawEmail, hint: Optional[str]) -> ExtractedEmail:
        """Execute Instructor structured extraction via OpenRouter."""
        prompt = (
            f"Analyze the following email and extract structured data:\n\n"
            f"From: {email.sender}\n"
            f"Domain: {email.sender_domain}\n"
            f"Subject: {email.subject}\n"
            f"Date: {email.date.isoformat()}\n"
            f"Classification Hint: {hint or 'Unknown'}\n\n"
            f"Snippet: {email.snippet}\n\n"
            f"Body:\n{email.body_plain[:2000]}\n"
        )

        response: ExtractedEmail = self._client.chat.completions.create(
            model=self.model,
            response_model=ExtractedEmail,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert email intelligence agent. Extract structured metadata "
                        "accurately. If the email contains a receipt/transaction, populate receipt_data. "
                        "If it contains a meeting/invite, populate meeting_data. "
                        "If it contains a bill due date or submission deadline, populate deadline_data."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_retries=2,
        )
        return response

    def _extract_heuristic(self, email: RawEmail, hint: Optional[str]) -> ExtractedEmail:
        """Deterministic heuristic extraction when LLM is unavailable."""
        subject_lower = email.subject.lower()
        body_lower = email.body_plain.lower()

        # Determine type
        if hint == "RECEIPT" or any(w in subject_lower for w in ["receipt", "invoice", "payment", "bill", "order"]):
            email_type = "receipt"
        elif hint == "MEETING" or any(w in subject_lower for w in ["invitation:", "invited", "zoom", "google meet"]):
            email_type = "meeting_invite"
        elif hint == "DEADLINE" or any(w in subject_lower for w in ["due by", "deadline", "pay by", "due date"]):
            email_type = "deadline"
        elif hint == "NEWSLETTER" or "unsubscribe" in body_lower:
            email_type = "newsletter"
        elif any(w in subject_lower for w in ["interview", "offer", "application", "role at", "recruiter"]):
            email_type = "job_related"
        elif hint == "PERSONAL":
            email_type = "personal"
        elif hint == "PROMOTIONAL":
            email_type = "promotional"
        else:
            email_type = "other"

        # Determine urgency & action required
        urgency = "low"
        action_required = False
        urgent_keywords = ["urgent", "immediately", "action required", "final notice", "asap", "overdue"]
        if any(w in subject_lower for w in urgent_keywords):
            urgency = "high"
            action_required = True
        elif email_type in ("deadline", "meeting_invite", "job_related"):
            urgency = "medium"
            action_required = True

        # Summary
        summary = f"{email.sender.split('<')[0].strip()}: {email.subject}"

        # Sub-entities
        receipt_data = self._heuristic_receipt(email) if email_type == "receipt" else None
        meeting_data = self._heuristic_meeting(email) if email_type == "meeting_invite" else None
        deadline_data = self._heuristic_deadline(email) if email_type == "deadline" else None

        return ExtractedEmail(
            email_type=email_type,  # type: ignore[arg-type]
            sender_domain=email.sender_domain,
            sender_email=email.sender_email,
            is_vip_sender=False,
            urgency=urgency,  # type: ignore[arg-type]
            action_required=action_required,
            summary=summary[:160],
            receipt_data=receipt_data,
            meeting_data=meeting_data,
            deadline_data=deadline_data,
        )

    def _heuristic_receipt(self, email: RawEmail) -> ReceiptData:
        """Extract vendor, amount, currency, and category deterministically."""
        # 1. Vendor
        vendor = email.sender.split("<")[0].strip().replace('"', "")
        if not vendor or vendor.lower() in ("receipt", "billing", "notifications", "support", "no-reply"):
            vendor = email.sender_domain.split(".")[0].capitalize()

        # 2. Currency & Amount
        text_to_search = f"{email.subject} \n {email.snippet} \n {email.body_plain[:1500]}"
        amount: Optional[float] = None
        currency = "INR"

        if "$" in text_to_search or "USD" in text_to_search:
            currency = "USD"
        elif "€" in text_to_search or "EUR" in text_to_search:
            currency = "EUR"
        elif "£" in text_to_search or "GBP" in text_to_search:
            currency = "GBP"

        # Regex for price pattern (handles ₹499.00, Rs. 1,299.50, $14.99, etc.)
        pattern = re.compile(
            r"(?:INR|Rs\.?|₹|\$|€|£)\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)",
            re.IGNORECASE,
        )
        match = pattern.search(text_to_search)
        if match:
            raw_amt = match.group(1).replace(",", "")
            try:
                amount = float(raw_amt)
            except ValueError:
                amount = None

        # 3. Category & Recurring
        combined_lower = f"{vendor} {email.subject} {email.snippet}".lower()
        category = "other"
        is_recurring = False

        food_brands = ["swiggy", "zomato", "ubereats", "doordash", "starbucks", "mcdonalds"]
        travel_brands = ["uber", "ola", "irctc", "makemytrip", "indigo", "airindia", "flight", "cab", "ride"]
        sub_brands = ["netflix", "spotify", "github copilot", "icloud", "apple", "youtube premium", "prime video", "medium", "patreon"]
        utility_brands = ["airtel", "jio", "bescom", "broadband", "fiber", "electricity", "water", "gas", "utility"]
        shopping_brands = ["amazon", "flipkart", "myntra", "blinkit", "zepto", "instamart"]
        software_brands = ["aws", "github", "google cloud", "vercel", "cloudflare", "digitalocean", "supabase", "postman"]

        if any(b in combined_lower for b in food_brands):
            category = "food"
        elif any(b in combined_lower for b in travel_brands):
            category = "travel"
        elif any(b in combined_lower for b in sub_brands):
            category = "subscription"
            is_recurring = True
        elif any(b in combined_lower for b in utility_brands):
            category = "utilities"
            is_recurring = True
        elif any(b in combined_lower for b in shopping_brands):
            category = "shopping"
        elif any(b in combined_lower for b in software_brands):
            category = "software"

        if "subscription" in combined_lower or "recurring" in combined_lower or "monthly membership" in combined_lower:
            is_recurring = True
            if category == "other":
                category = "subscription"

        # 4. Date
        receipt_date = email.date.date() if isinstance(email.date, dt.datetime) else None

        return ReceiptData(
            vendor=vendor[:60],
            amount=amount,
            currency=currency,
            date=receipt_date,
            category=category,
            is_recurring=is_recurring,
        )

    def _heuristic_meeting(self, email: RawEmail) -> MeetingData:
        """Extract title, datetime, link, and organizer from meeting invites."""
        title = email.subject.replace("Invitation: ", "").replace("Updated invitation: ", "").strip()
        
        # Link detection (Google Meet, Zoom, Teams)
        link: Optional[str] = None
        meet_match = re.search(r"https?://(?:meet\.google\.com/[a-z-]+|zoom\.us/j/[0-9\?&=]+|teams\.microsoft\.com/[^\s>]+)", email.body_plain)
        if meet_match:
            link = meet_match.group(0)

        return MeetingData(
            title=title or "Meeting",
            datetime_start=email.date,
            location_or_link=link,
            organizer=email.sender,
        )

    def _heuristic_deadline(self, email: RawEmail) -> DeadlineData:
        """Extract deadline description, due date, and source context."""
        description = email.subject.strip()
        due_date = (email.date + dt.timedelta(days=7)).date() if isinstance(email.date, dt.datetime) else None

        # Try to find a date pattern in subject or snippet
        date_match = re.search(r"\b(?:due|by|before)\s+([A-Za-z]+ \d{1,2}(?:, \d{4})?|\d{1,2}/\d{1,2}/\d{2,4})\b", f"{email.subject} {email.snippet}", re.IGNORECASE)
        context = email.snippet or email.subject

        return DeadlineData(
            description=description,
            due_date=due_date,
            source_context=context[:150],
        )
