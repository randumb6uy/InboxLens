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

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
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
                    classification = excluded.classification,
                    matched_rule = excluded.matched_rule,
                    confidence = excluded.confidence;
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
