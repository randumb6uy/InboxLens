"""SQLite database storage and repository layer for IndexLens."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.config import BASE_DIR
from src.schemas.email_schemas import RawEmail

DEFAULT_DB_PATH = BASE_DIR / "indexlens.db"


import contextlib
from collections.abc import Generator


class Database:
    """Manages SQLite connection and provides schema queries."""

    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextlib.contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """Create tables and indexes if they do not exist."""
        with self.get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS emails (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT,
                    sender TEXT,
                    sender_email TEXT,
                    sender_domain TEXT,
                    recipient TEXT,
                    subject TEXT,
                    date TEXT,
                    snippet TEXT,
                    body_plain TEXT,
                    labels TEXT,
                    classification TEXT,
                    matched_rule TEXT,
                    confidence REAL,
                    created_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_emails_sender_email ON emails(sender_email);
                CREATE INDEX IF NOT EXISTS idx_emails_sender_domain ON emails(sender_domain);
                CREATE INDEX IF NOT EXISTS idx_emails_classification ON emails(classification);
                CREATE INDEX IF NOT EXISTS idx_emails_date ON emails(date);

                CREATE TABLE IF NOT EXISTS receipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id TEXT UNIQUE,
                    vendor TEXT,
                    amount REAL,
                    currency TEXT DEFAULT 'INR',
                    date TEXT,
                    category TEXT,
                    is_recurring INTEGER DEFAULT 0,
                    FOREIGN KEY(email_id) REFERENCES emails(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_receipts_vendor ON receipts(vendor);
                CREATE INDEX IF NOT EXISTS idx_receipts_category ON receipts(category);

                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vendor TEXT UNIQUE,
                    cadence TEXT DEFAULT 'monthly',
                    last_amount REAL,
                    currency TEXT DEFAULT 'INR',
                    last_charge_date TEXT,
                    next_expected_date TEXT,
                    status TEXT DEFAULT 'active'
                );

                CREATE TABLE IF NOT EXISTS meetings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id TEXT UNIQUE,
                    title TEXT,
                    datetime_start TEXT,
                    location_or_link TEXT,
                    organizer TEXT,
                    FOREIGN KEY(email_id) REFERENCES emails(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS deadlines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id TEXT UNIQUE,
                    description TEXT,
                    due_date TEXT,
                    source_context TEXT,
                    FOREIGN KEY(email_id) REFERENCES emails(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS important_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE,
                    display_name TEXT,
                    domain TEXT,
                    notes TEXT
                );
                """
            )

    def upsert_email(
        self,
        email: RawEmail,
        classification: str,
        matched_rule: str = "",
        confidence: float = 0.0,
    ) -> None:
        """Insert or update raw email and its classification result."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO emails (
                    id, thread_id, sender, sender_email, sender_domain, recipient,
                    subject, date, snippet, body_plain, labels,
                    classification, matched_rule, confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    classification = CASE WHEN emails.matched_rule = 'llm_extraction' AND excluded.classification = 'NEEDS_LLM' THEN emails.classification ELSE excluded.classification END,
                    matched_rule = CASE WHEN emails.matched_rule = 'llm_extraction' AND excluded.classification = 'NEEDS_LLM' THEN emails.matched_rule ELSE excluded.matched_rule END,
                    confidence = CASE WHEN emails.matched_rule = 'llm_extraction' AND excluded.classification = 'NEEDS_LLM' THEN emails.confidence ELSE excluded.confidence END;
                """,
                (
                    email.id,
                    email.thread_id,
                    email.sender,
                    email.sender_email,
                    email.sender_domain,
                    email.recipient,
                    email.subject,
                    email.date.isoformat(),
                    email.snippet,
                    email.body_plain,
                    json.dumps(email.labels),
                    classification,
                    matched_rule,
                    confidence,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def get_email(self, email_id: str) -> Optional[dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM emails WHERE id = ?", (email_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_emails(
        self,
        classification: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            if classification:
                cursor = conn.execute(
                    "SELECT * FROM emails WHERE classification = ? ORDER BY date DESC LIMIT ? OFFSET ?",
                    (classification, limit, offset),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM emails ORDER BY date DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                )
            return [dict(r) for r in cursor.fetchall()]

    def get_classification_stats(self) -> dict[str, Any]:
        """Compute aggregate counts and cost efficiency of deterministic routing."""
        with self.get_connection() as conn:
            total_count = conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
            if total_count == 0:
                return {"total": 0, "breakdown": {}, "deterministic_rate": 0.0}

            cursor = conn.execute(
                "SELECT classification, COUNT(*) as cnt FROM emails GROUP BY classification ORDER BY cnt DESC"
            )
            breakdown = {row["classification"]: row["cnt"] for row in cursor.fetchall()}
            needs_llm = breakdown.get("NEEDS_LLM", 0)
            deterministic_count = total_count - needs_llm
            rate = (deterministic_count / total_count) * 100.0

            return {
                "total": total_count,
                "deterministic_count": deterministic_count,
                "needs_llm_count": needs_llm,
                "deterministic_rate": round(rate, 2),
                "breakdown": breakdown,
            }

    def update_email_classification(
        self,
        email_id: str,
        classification: str,
        matched_rule: str = "llm_extraction",
        confidence: float = 0.95,
        summary: Optional[str] = None,
    ) -> None:
        """Update an email's classification and snippet after LLM resolution."""
        with self.get_connection() as conn:
            if summary:
                conn.execute(
                    """
                    UPDATE emails
                    SET classification = ?, matched_rule = ?, confidence = ?, snippet = ?
                    WHERE id = ?
                    """,
                    (classification.upper(), matched_rule, confidence, summary, email_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE emails
                    SET classification = ?, matched_rule = ?, confidence = ?
                    WHERE id = ?
                    """,
                    (classification.upper(), matched_rule, confidence, email_id),
                )

    def add_vip_contact(self, email: str, display_name: str = "", notes: str = "") -> None:
        domain = email.split("@")[-1].lower() if "@" in email else ""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO important_contacts (email, display_name, domain, notes)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET
                    display_name = excluded.display_name,
                    notes = excluded.notes;
                """,
                (email.lower().strip(), display_name, domain, notes),
            )

    def get_vip_contacts(self) -> set[str]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT email FROM important_contacts")
            return {row["email"] for row in cursor.fetchall()}

    def insert_receipt(
        self,
        email_id: str,
        vendor: str,
        amount: float,
        currency: str = "INR",
        date: str = "",
        category: str = "other",
        is_recurring: bool = False,
    ) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO receipts (email_id, vendor, amount, currency, date, category, is_recurring)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(email_id) DO UPDATE SET
                    vendor = excluded.vendor,
                    amount = excluded.amount,
                    currency = excluded.currency,
                    date = excluded.date,
                    category = excluded.category,
                    is_recurring = excluded.is_recurring;
                """,
                (email_id, vendor, amount, currency, date, category, 1 if is_recurring else 0),
            )

    def insert_subscription(
        self,
        vendor: str,
        cadence: str = "monthly",
        last_amount: float = 0.0,
        currency: str = "INR",
        last_charge_date: str = "",
        next_expected_date: str = "",
        status: str = "active",
    ) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO subscriptions (vendor, cadence, last_amount, currency, last_charge_date, next_expected_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(vendor) DO UPDATE SET
                    cadence = excluded.cadence,
                    last_amount = excluded.last_amount,
                    currency = excluded.currency,
                    last_charge_date = excluded.last_charge_date,
                    next_expected_date = excluded.next_expected_date,
                    status = excluded.status;
                """,
                (vendor, cadence, last_amount, currency, last_charge_date, next_expected_date, status),
            )

    def insert_meeting(
        self,
        email_id: str,
        title: str,
        datetime_start: str = "",
        location_or_link: str = "",
        organizer: str = "",
    ) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO meetings (email_id, title, datetime_start, location_or_link, organizer)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(email_id) DO UPDATE SET
                    title = excluded.title,
                    datetime_start = excluded.datetime_start,
                    location_or_link = excluded.location_or_link,
                    organizer = excluded.organizer;
                """,
                (email_id, title, datetime_start, location_or_link, organizer),
            )

    def insert_deadline(
        self,
        email_id: str,
        description: str,
        due_date: str = "",
        source_context: str = "",
    ) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO deadlines (email_id, description, due_date, source_context)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(email_id) DO UPDATE SET
                    description = excluded.description,
                    due_date = excluded.due_date,
                    source_context = excluded.source_context;
                """,
                (email_id, description, due_date, source_context),
            )

    def get_unextracted_emails(self, limit: int = 100) -> list[RawEmail]:
        """Fetch emails that require entity extraction and are not yet extracted into child tables."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM emails e
                WHERE (
                    (e.classification = 'RECEIPT' AND NOT EXISTS (SELECT 1 FROM receipts r WHERE r.email_id = e.id))
                    OR (e.classification = 'MEETING' AND NOT EXISTS (SELECT 1 FROM meetings m WHERE m.email_id = e.id))
                    OR (e.classification = 'DEADLINE' AND NOT EXISTS (SELECT 1 FROM deadlines d WHERE d.email_id = e.id))
                    OR e.classification = 'NEEDS_LLM'
                )
                ORDER BY e.date DESC
                LIMIT ?;
                """,
                (limit,),
            )
            emails = []
            for row in cursor.fetchall():
                try:
                    dt_val = datetime.fromisoformat(row["date"])
                except Exception:
                    dt_val = datetime.now(timezone.utc)

                labels_list = []
                if row["labels"]:
                    try:
                        labels_list = json.loads(row["labels"])
                    except Exception:
                        pass

                emails.append(
                    RawEmail(
                        id=row["id"],
                        thread_id=row["thread_id"] or row["id"],
                        sender=row["sender"],
                        sender_email=row["sender_email"],
                        sender_domain=row["sender_domain"],
                        recipient=row["recipient"],
                        subject=row["subject"] or "",
                        date=dt_val,
                        snippet=row["snippet"] or "",
                        body_plain=row["body_plain"] or "",
                        labels=labels_list,
                    )
                )
            return emails

    def get_overview_metrics(self) -> dict[str, Any]:
        """Aggregate high-level metrics for dashboard header cards."""
        with self.get_connection() as conn:
            total_spend_row = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM receipts").fetchone()
            total_spend = total_spend_row[0] if total_spend_row else 0.0

            active_subs_count = conn.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'").fetchone()[0]
            upcoming_deadlines_count = conn.execute("SELECT COUNT(*) FROM deadlines").fetchone()[0]
            vip_emails_count = conn.execute(
                "SELECT COUNT(*) FROM emails WHERE classification = 'PERSONAL' OR sender_email IN (SELECT email FROM important_contacts)"
            ).fetchone()[0]

            return {
                "total_spend_this_month": round(total_spend, 2),
                "currency": "INR",
                "active_subscriptions_count": active_subs_count,
                "upcoming_deadlines_count": upcoming_deadlines_count,
                "vip_emails_count": vip_emails_count,
            }

    def get_spend_analytics(self) -> dict[str, Any]:
        """Category breakdown, monthly trend, and transactions for the Financial tab."""
        with self.get_connection() as conn:
            # Spend by category
            cat_cursor = conn.execute(
                """
                SELECT COALESCE(category, 'other') as category, SUM(amount) as total, COUNT(*) as count
                FROM receipts
                GROUP BY category
                ORDER BY total DESC;
                """
            )
            by_category = [dict(r) for r in cat_cursor.fetchall()]

            # Recent transactions
            tx_cursor = conn.execute(
                """
                SELECT r.id, r.vendor, r.amount, r.currency, r.date, r.category, r.is_recurring,
                       e.subject, e.sender, e.snippet
                FROM receipts r
                LEFT JOIN emails e ON r.email_id = e.id
                ORDER BY r.date DESC
                LIMIT 50;
                """
            )
            transactions = [dict(r) for r in tx_cursor.fetchall()]

            # Real spend trend from extracted receipts
            # If multiple months, group by month (YYYY-MM); if within single month, group by day (MM-DD)
            month_count_row = conn.execute("SELECT COUNT(DISTINCT substr(date, 1, 7)) FROM receipts;").fetchone()
            month_count = month_count_row[0] if month_count_row else 0
            if month_count > 1:
                trend_cursor = conn.execute(
                    """
                    SELECT substr(date, 1, 7) as period, SUM(amount) as spend
                    FROM receipts
                    GROUP BY period
                    ORDER BY period ASC;
                    """
                )
            else:
                trend_cursor = conn.execute(
                    """
                    SELECT substr(date, 6, 5) as period, SUM(amount) as spend
                    FROM receipts
                    GROUP BY period
                    ORDER BY period ASC;
                    """
                )
            spend_trend = [{"month": r["period"], "spend": round(r["spend"], 2)} for r in trend_cursor.fetchall()]

            return {
                "categories": by_category,
                "transactions": transactions,
                "total_transactions": len(transactions),
                "spend_trend": spend_trend,
            }


    def list_subscriptions(self) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM subscriptions ORDER BY last_amount DESC")
            return [dict(r) for r in cursor.fetchall()]

    def list_newsletters(self) -> list[dict[str, Any]]:
        import re
        unsubscribe_regex = re.compile(r"https?://[^\s>]+(?:unsubscribe|opt-out)[^\s>]*", re.IGNORECASE)
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT sender, sender_email, sender_domain, subject, date, body_plain FROM emails WHERE classification = 'NEWSLETTER' ORDER BY date DESC"
            )
            senders_map: dict[str, dict[str, Any]] = {}
            for row in cursor.fetchall():
                email_addr = row["sender_email"]
                if email_addr not in senders_map:
                    # Find unsubscribe URL in body
                    match = unsubscribe_regex.search(row["body_plain"])
                    unsub_url = match.group(0) if match else f"https://{row['sender_domain']}"
                    senders_map[email_addr] = {
                        "name": row["sender"].split("<")[0].strip() or row["sender_domain"],
                        "email": email_addr,
                        "domain": row["sender_domain"],
                        "last_subject": row["subject"],
                        "last_received": row["date"],
                        "frequency": "Weekly",
                        "unsubscribe_url": unsub_url,
                        "volume_count": 1,
                    }
                else:
                    senders_map[email_addr]["volume_count"] += 1

            return list(senders_map.values())

    def list_upcoming_schedule(self) -> dict[str, Any]:
        with self.get_connection() as conn:
            meetings_cursor = conn.execute(
                "SELECT m.*, e.subject, e.sender FROM meetings m LEFT JOIN emails e ON m.email_id = e.id ORDER BY m.datetime_start ASC"
            )
            meetings = [dict(r) for r in meetings_cursor.fetchall()]

            deadlines_cursor = conn.execute(
                "SELECT d.*, e.subject, e.sender FROM deadlines d LEFT JOIN emails e ON d.email_id = e.id ORDER BY d.due_date ASC"
            )
            deadlines = [dict(r) for r in deadlines_cursor.fetchall()]

            return {"meetings": meetings, "deadlines": deadlines}

    def list_job_opportunities(self) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, sender, sender_email, sender_domain, subject, date, snippet
                FROM emails
                WHERE LOWER(subject) LIKE '%interview%'
                   OR LOWER(subject) LIKE '%offer%'
                   OR LOWER(subject) LIKE '%career%'
                   OR LOWER(subject) LIKE '%role%'
                   OR LOWER(subject) LIKE '%hiring%'
                   OR LOWER(subject) LIKE '%roadmap%'
                ORDER BY date DESC;
                """
            )
            jobs = []
            for row in cursor.fetchall():
                company = row["sender_domain"].split(".")[0].capitalize()
                jobs.append({
                    "id": row["id"],
                    "company": company or "Tech Partner",
                    "role": row["subject"][:40],
                    "sender": row["sender"],
                    "date": row["date"][:10],
                    "status": "Interview Scheduled" if "interview" in row["subject"].lower() else "New Inbound",
                    "snippet": row["snippet"],
                })

            return jobs

    def search_emails(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search emails matching terms in subject, snippet, sender, or body."""
        import re
        clean_q = query.strip().lower()
        if not clean_q:
            return []

        stopwords = {
            "what", "when", "where", "which", "who", "whom", "this", "that", "these", "those",
            "have", "has", "had", "does", "did", "doing", "the", "and", "but", "about", "from",
            "with", "tell", "show", "find", "give", "much", "many", "more", "some", "any", "how",
            "are", "was", "were", "been", "for", "say", "said"
        }
        raw_tokens = [re.sub(r"[^a-zA-Z0-9]", "", t) for t in clean_q.split()]
        tokens = [t for t in raw_tokens if len(t) > 2 and t not in stopwords]
        if not tokens:
            tokens = [t for t in raw_tokens if len(t) > 2] or [clean_q]

        clauses = []
        params = []
        score_cases = []
        for token in tokens[:5]:
            p = f"%{token}%"
            clauses.append(
                "(LOWER(subject) LIKE ? OR LOWER(snippet) LIKE ? OR LOWER(sender) LIKE ? OR LOWER(body_plain) LIKE ?)"
            )
            params.extend([p, p, p, p])
            score_cases.append(
                "(CASE WHEN LOWER(subject) LIKE ? THEN 3 ELSE 0 END + "
                "CASE WHEN LOWER(snippet) LIKE ? THEN 2 ELSE 0 END + "
                "CASE WHEN LOWER(sender) LIKE ? THEN 2 ELSE 0 END + "
                "CASE WHEN LOWER(body_plain) LIKE ? THEN 1 ELSE 0 END)"
            )

        where_sql = " OR ".join(clauses) if clauses else "1=1"
        score_sql = " + ".join(score_cases) if score_cases else "0"

        # Combine params: score params + where params + limit
        all_params = list(params) + list(params) + [limit]

        with self.get_connection() as conn:
            cursor = conn.execute(
                f"""
                SELECT id, sender, sender_email, sender_domain, subject, date, snippet, classification,
                       ({score_sql}) AS match_score
                FROM emails
                WHERE {where_sql}
                ORDER BY match_score DESC, date DESC
                LIMIT ?;
                """,
                tuple(all_params),
            )
            return [dict(r) for r in cursor.fetchall()]

