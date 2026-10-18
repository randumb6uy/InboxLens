"""Deterministic regex and keyword router for zero-cost email classification."""

import re
from typing import Literal, NamedTuple
from src.schemas.email_schemas import RawEmail

ClassificationType = Literal[
    "RECEIPT",
    "NEWSLETTER",
    "PROMOTIONAL",
    "PERSONAL",
    "MEETING",
    "DEADLINE",
    "NEEDS_LLM",
]


class RouteResult(NamedTuple):
    category: ClassificationType
    matched_rule: str
    confidence: float


# Common receipt & financial patterns
RECEIPT_SUBJECT_REGEX = re.compile(
    r"\b(receipt|invoice|bill|order\s+delivered|order\s+confirmation|payment\s+receipt|payment\s+confirmed|membership\s+fee|e-?bill|statement|debited|tax\s+invoice)\b",
    re.IGNORECASE,
)
RECEIPT_BODY_REGEX = re.compile(
    r"(total\s*[:=]\s*(?:[₹$€£]|INR|Rs\.?|USD|EUR|GBP)\s*[\d,]+(?:\.\d{2})?|amount\s+charged|amount\s+paid|subtotal|billing\s+date|payment\s+date|gstin|invoice\s*#)",
    re.IGNORECASE,
)
RECEIPT_DOMAINS = {
    "uber.com",
    "swiggy.in",
    "zomato.com",
    "amazon.in",
    "amazon.com",
    "apple.com",
    "netflix.com",
    "spotify.com",
    "airtel.com",
    "github.com",
    "stripe.com",
    "razorpay.com",
}

# Newsletter & Digest patterns
NEWSLETTER_DOMAINS = {
    "substack.com",
    "pragmaticengineer.com",
    "tldr.tech",
    "bytebytego.com",
    "morningbrew.com",
    "theverge.com",
    "hackernews.com",
    "medium.com",
}
NEWSLETTER_BODY_REGEX = re.compile(
    r"\b(unsubscribe|opt-out|manage\s+your\s+preferences|view\s+in\s+browser|this\s+edition|issue\s+#\d+)\b",
    re.IGNORECASE,
)

# Promotional & Marketing patterns
PROMO_DOMAINS = {
    "makemytrip.com",
    "myntra.com",
    "flipkart.com",
    "ajio.com",
    "goibibo.com",
}
PROMO_SUBJECT_REGEX = re.compile(
    r"\b(\d+%\s*(?:off|discount|savings)|flat\s+₹?\d+|sale\b|mega\s+deal|exclusive\s+offer|hurry|coupon|discount|special\s+price|save\s+\d+%?)\b",
    re.IGNORECASE,
)

# Calendar & Meetings
MEETING_DOMAINS = {"calendar-notification@google.com", "calendar-invitations@google.com"}
MEETING_SUBJECT_REGEX = re.compile(r"\b(invitation\s*:|invited\s+you\s+to|meeting\s+scheduled|sync\s*@|zoom\s+meeting)\b", re.IGNORECASE)

# Deadlines
DEADLINE_REGEX = re.compile(
    r"\b(due\s+date\s*[:=]|due\s+on\s*[:=]|payment\s+due|due\s+by\s*[:=]|submit\s+(?:before|by)|deadline\s*[:=]|last\s+date\s+to)\b",
    re.IGNORECASE,
)


# Thread reply & forward patterns (handles [EXTERNAL] Re: etc.)
RE_FWD_REGEX = re.compile(r"^(?:\[[^\]]+\]\s*)*(?:re|fwd|fw)\s*:\s*", re.IGNORECASE)


class EmailRouter:
    """Classifies raw emails using deterministic heuristics with zero LLM API cost."""

    def __init__(self, vip_contacts: set[str] | None = None):
        self.vip_contacts = {c.lower().strip() for c in (vip_contacts or set())}

    def route(self, email: RawEmail) -> RouteResult:
        """Route an email to a primary category or escalate to NEEDS_LLM."""
        subject = (email.subject or "").lower().strip()
        body = (email.body_plain or "").lower()
        sender_email = (email.sender_email or "").lower().strip()
        sender_domain = (email.sender_domain or "").lower().strip()

        # 1. VIP contacts take precedence for personal triage
        if sender_email in self.vip_contacts:
            return RouteResult("PERSONAL", "vip_sender_match", 1.0)

        # 2. Calendar / Meeting Invites
        if sender_email in MEETING_DOMAINS or MEETING_SUBJECT_REGEX.search(subject):
            return RouteResult("MEETING", "meeting_pattern_match", 0.95)

        # 3. Known promotional senders or discount keywords
        if sender_domain in PROMO_DOMAINS or PROMO_SUBJECT_REGEX.search(subject):
            return RouteResult("PROMOTIONAL", "promo_domain_or_subject", 0.95)

        # 4. Receipts & Bills
        is_receipt_domain = sender_domain in RECEIPT_DOMAINS
        has_receipt_subject = bool(RECEIPT_SUBJECT_REGEX.search(subject))
        has_receipt_body = bool(RECEIPT_BODY_REGEX.search(body))

        if (is_receipt_domain and (has_receipt_subject or has_receipt_body)) or (has_receipt_subject and has_receipt_body):
            return RouteResult("RECEIPT", "receipt_domain_and_keywords", 0.95)

        # 5. Newsletters
        is_newsletter_domain = sender_domain in NEWSLETTER_DOMAINS
        has_newsletter_body = bool(NEWSLETTER_BODY_REGEX.search(body))

        if is_newsletter_domain or ("newsletter" in subject and has_newsletter_body):
            return RouteResult("NEWSLETTER", "newsletter_heuristics", 0.95)

        # 6. Deadlines
        if DEADLINE_REGEX.search(subject) or DEADLINE_REGEX.search(body):
            return RouteResult("DEADLINE", "deadline_keywords", 0.85)

        # 7. Personal (Direct one-on-one correspondence)
        if RE_FWD_REGEX.search(subject):
            # Likely an ongoing human conversation if not an automated newsletter
            if not has_newsletter_body:
                return RouteResult("PERSONAL", "conversation_thread_reply", 0.80)

        # If it has receipt keywords but lacks clear structural evidence, route to LLM
        if is_receipt_domain or has_receipt_subject or has_receipt_body:
            return RouteResult("NEEDS_LLM", "ambiguous_receipt_candidate", 0.50)

        # Default fallback: Needs LLM classification
        return RouteResult("NEEDS_LLM", "no_deterministic_rule_matched", 0.0)
