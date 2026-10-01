"""Semantic and template cache to prevent duplicate LLM extractions."""

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from src.config import BASE_DIR

logger = logging.getLogger(__name__)

DEFAULT_CACHE_FILE = BASE_DIR / ".cache" / "extraction_cache.json"


class ExtractionCache:
    """Hash and template-based cache for LLM extraction results."""

    def __init__(self, cache_file: Optional[Path | str] = DEFAULT_CACHE_FILE):
        self.cache_file = Path(cache_file) if cache_file else None
        self._cache: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load cache from disk if file exists."""
        if not self.cache_file:
            return
        try:
            if self.cache_file.exists():
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                logger.debug("Loaded %d cached extraction records", len(self._cache))
        except Exception as err:
            logger.warning("Failed to load extraction cache: %s", err)
            self._cache = {}

    def save(self) -> None:
        """Persist cache to disk."""
        if not self.cache_file:
            return
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
        except Exception as err:
            logger.warning("Failed to save extraction cache: %s", err)

    @staticmethod
    def generate_cache_key(
        sender_domain: str,
        subject: str,
        body_sample: str,
    ) -> str:
        """Generate a stable fingerprint key for an email.
        
        Normalizes variable noise (numbers, dates, transaction IDs)
        to identify identical receipt/template formats from the same sender.
        """
        # Normalize subject: strip digits, ordinals, dates
        norm_subject = re.sub(r"\d+", "<NUM>", subject.lower().strip())
        norm_subject = re.sub(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", "<MONTH>", norm_subject)
        
        # Take first 300 characters of body, normalize numbers
        body_prefix = body_sample[:300].lower()
        norm_body = re.sub(r"\d+", "<NUM>", body_prefix)

        key_str = f"{sender_domain.lower()}::{norm_subject}::{norm_body}"
        return hashlib.sha256(key_str.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[dict[str, Any]]:
        """Retrieve cached result by key."""
        return self._cache.get(key)

    def set(self, key: str, value: dict[str, Any]) -> None:
        """Store extraction result in cache and auto-persist."""
        self._cache[key] = value
        self.save()

    def has(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self._cache

    def clear(self) -> None:
        """Clear all cached records."""
        self._cache.clear()
        if self.cache_file and self.cache_file.exists():
            try:
                self.cache_file.unlink()
            except Exception:
                pass

    def __len__(self) -> int:
        return len(self._cache)
