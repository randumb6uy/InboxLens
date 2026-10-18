"""Application configuration and environment settings."""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")

# OAuth2 & Gmail API configuration
GMAIL_CREDENTIALS_PATH = Path(os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json"))
GMAIL_TOKEN_PATH = Path(os.getenv("GMAIL_TOKEN_PATH", "token.json"))
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Mode flag: If MOCK_GMAIL is true or credentials.json doesn't exist, allow fallback to synthetic data
_mock_env = os.getenv("MOCK_GMAIL", "").lower()
MOCK_GMAIL = _mock_env in ("1", "true", "yes")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'indexlens.db'}")

# OpenRouter (Phase 2)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
EXTRACTION_MODEL = os.getenv("EXTRACTION_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
ANOMALY_MODEL = os.getenv("ANOMALY_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
