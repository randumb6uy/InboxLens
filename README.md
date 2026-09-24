# IndexLens — AI-Powered Gmail Data & Stats Agent

IndexLens is an AI-first Gmail intelligence engine that ingests emails via the official Gmail API, deterministically classifies them, extracts structured entities using tiered LLMs, and surfaces actionable analytics via a multi-tab dashboard and RAG Q&A interface.

## Architecture

- **Ingestion**: Gmail API (OAuth2 `gmail.readonly`), batch nightly sync.
- **Router**: Deterministic regex/keyword rules (handles 60-70% zero-cost).
- **Extraction**: OpenRouter (tiered models) + Pydantic + `instructor`.
- **Storage**: SQLite / Postgres + Vector store (Chroma / pgvector).
- **Dashboard**: Multi-tab Next.js UI + FastAPI REST API.

## Quick Start

1. Set up your `.env` file:
   ```bash
   cp .env.example .env
   ```

2. To run with live Gmail, follow the step-by-step setup in [GMAIL_SETUP.md](GMAIL_SETUP.md) and place your `credentials.json` in the root directory.
   To run in demo/offline mode without Google credentials, set `MOCK_GMAIL=true` in `.env`.

3. Run Phase 0 ingestion test:
   ```bash
   python -m src.cli fetch --limit 100
   ```
