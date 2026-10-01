# IndexLens — Technical Architecture

## 1. High-Level Data Flow

```
Gmail API (OAuth2, readonly)
        ↓
Regex/Keyword Router  ──────────────→ [70% of emails: classified, zero LLM cost]
        ↓ (ambiguous ~30%)
OpenRouter LLM (tiered by task)
        ↓
Pydantic-validated structured extraction
        ↓
   ┌────────────────────┬─────────────────────┐
Categorization Agent   Anomaly Agent      Embedding (bge-small)
   └────────────────────┴─────────────────────┘
        ↓
Structured DB (SQLite/Postgres)  +  Vector Store (Chroma/pgvector)
        ↓
   ┌─────────────────────┬──────────────────────┐
Stats Dashboard (SQL)   RAG Q&A (hybrid search    Weekly Digest Agent
                          + reranker + LLM)        (LLM synthesis)
```

## 2. Component Breakdown

### 2.1 Ingestion Layer
- **Gmail API** (`google-api-python-client`, OAuth2, `gmail.readonly` scope)
- `users.messages.list` for paging, `users.messages.get` for full content
- `users.history.list` for incremental sync after first full pull (avoids re-fetching entire inbox each run)
- Runs as a **batch job** (nightly cron / scheduled task), not real-time — controls cost and respects API quotas

### 2.2 Router (Deterministic Layer)
- Pure Python regex/keyword matching, no external calls, 0ms overhead
- Classifies into: `RECEIPT`, `NEWSLETTER`, `PROMOTIONAL`, `PERSONAL`, `NEEDS_LLM`
- Known newsletter/promo sender domains maintained as a local list, expanded over time
- Only `NEEDS_LLM` bucket proceeds to the extraction layer

### 2.3 Extraction Layer (LLM)
- **Provider:** OpenRouter (`https://openrouter.ai/api/v1`, OpenAI-compatible)
- **Model tiering by task:**
  | Task | Model | Rationale |
  |---|---|---|
  | Bulk classification/extraction | `google/gemini-2.5-flash-lite` or `deepseek/deepseek-chat` | Cheap, fast, sufficient for structured extraction |
  | Anomaly/ambiguous judgment | `anthropic/claude-3.5-haiku` | Better reasoning, still low-cost |
  | Weekly digest synthesis | `anthropic/claude-sonnet-4` | Higher quality writing; called once/week, cost negligible |
- **Library:** `instructor` wrapping the OpenAI client, enforcing Pydantic schemas directly on LLM output
- **Caching:** Redis (or in-memory dict early on) with semantic similarity check (cosine ≥ 0.96) before calling the LLM, to avoid re-processing near-duplicate content

### 2.4 Data Schemas (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date, datetime

class ReceiptData(BaseModel):
    vendor: str
    amount: Optional[float]
    currency: str = "INR"
    date: Optional[date]
    category: str  # e.g. "food", "subscription", "travel", "utilities"
    is_recurring: Optional[bool] = None  # heuristic flag for subscription detection

class MeetingData(BaseModel):
    title: str
    datetime_start: Optional[datetime]
    location_or_link: Optional[str]
    organizer: Optional[str]

class DeadlineData(BaseModel):
    description: str
    due_date: Optional[date]
    source_context: str  # short excerpt giving context

class ExtractedEmail(BaseModel):
    email_type: Literal["receipt", "personal", "job_related", "travel", "bill",
                          "meeting_invite", "deadline", "newsletter", "other"]
    sender_domain: str
    sender_email: str
    is_vip_sender: bool = False  # matched against user-defined important-contacts list
    urgency: Literal["low", "medium", "high"]
    action_required: bool
    summary: str = Field(description="One sentence summary")
    receipt_data: Optional[ReceiptData] = None
    meeting_data: Optional[MeetingData] = None
    deadline_data: Optional[DeadlineData] = None
```

### 2.5 Storage Layer
- **Structured store:** SQLite for personal-scale use (thousands to tens of thousands of emails); Postgres if multi-user or deployed
- **Vector store:** Chroma (embedded, simplest) or pgvector if already running Postgres — no need for Qdrant/Milvus-scale distribution at this volume
- **Embedding model:** `BAAI/bge-small-en-v1.5`, runs locally on CPU (no API cost, keeps content local for this step)

Core tables (conceptual):
- `emails` — raw metadata (id, sender, subject, date, gmail_thread_id)
- `extracted_data` — structured fields per email (foreign key to `emails`)
- `receipts` — normalized receipt records for aggregation queries
- `subscriptions` — derived/materialized view over `receipts`: vendor, cadence, last charge date, next expected date, price history
- `meetings` — extracted meeting/invite records (title, datetime, location, organizer)
- `deadlines` — extracted deadline records (description, due date, source email)
- `important_contacts` — user-maintained VIP list (email/domain, optional display name)
- `embeddings` — vector store reference (or separate Chroma collection keyed by email id)

### 2.6 Multi-Agent Layer
- **Supervisor** orchestrates the pipeline per batch run
- **Extraction Agent** — fills `ExtractedEmail`/`ReceiptData` schemas
- **Categorization Agent** — assigns/refines spend categories using vendor history + context
- **Anomaly Agent** — flags: spend spikes vs. historical baseline, first-time senders requesting payment (phishing signal), subscription price increases
- **Digest Agent** — synthesizes the week's structured facts into a natural-language summary (LLM call, low volume)

Agents run sequentially where output feeds the next (Extraction → Categorization/Anomaly in parallel → Digest last), coordinated by the Supervisor, not a fixed hardcoded script.

### 2.7 Query Layer (Stats + RAG)
- **Stats questions** ("how much did I spend on X") → router detects intent → runs SQL aggregation directly → LLM only phrases the final answer in natural language (never does the math itself)
- **Semantic questions** ("what did the landlord say about Y") → hybrid retrieval:
  1. BM25 keyword search + dense vector search (Reciprocal Rank Fusion to combine)
  2. Cross-encoder reranker (`ms-marco-MiniLM-L-6-v2`) narrows to top-1/2 most relevant email(s)
  3. LLM synthesizes an answer grounded in the retrieved email content

### 2.8 Presentation Layer — Multi-Tab React Dashboard

Built directly as a **Next.js (React) frontend + FastAPI backend**, structured as a single-page app with five tabs, each backed by its own API route:

| Tab | Data source | Primary API endpoint |
|---|---|---|
| Financial Statistics | `receipts` table, aggregated | `GET /api/stats/spend?range=month` |
| Active Subscriptions | `subscriptions` table | `GET /api/subscriptions` |
| Newsletters | `emails` filtered by `email_type=newsletter` | `GET /api/newsletters` |
| Important Contacts | `emails` filtered by `is_vip_sender=true`, joined with `important_contacts` | `GET /api/contacts/important` |
| Meetings & Deadlines | `meetings` + `deadlines` tables, merged and date-sorted | `GET /api/schedule/upcoming` |

- **Frontend stack:** Next.js, Tailwind CSS for styling, Recharts for financial charts, a simple tab/router component (React state or Next.js route segments) to switch between the five views
- **Backend stack:** FastAPI serving REST endpoints above; each endpoint runs a direct SQL aggregation query (no LLM call at request time — all LLM extraction already happened during the batch ingestion job, so the dashboard itself is fast and free to load)
- **Important Contacts logic:** VIP list is either manually maintained by the user (add/remove sender emails via a simple settings tab) or bootstrapped by inferring frequent two-way correspondence (reply rate + reply speed) from the ingested email metadata
- **Meetings & Deadlines logic:** meeting invites detected via `.ics` attachment presence or calendar-invite-style subject/body patterns (regex first pass); deadlines detected via keyword patterns ("due by," "deadline," "submit before") escalated to the LLM extraction layer when the date isn't unambiguous from regex alone
- **Refresh cadence:** dashboard data reflects the last completed batch ingestion run (nightly); a manual "sync now" button can trigger an on-demand ingestion pass for the impatient

## 3. Privacy & Security Notes
- Gmail OAuth token stored locally, never committed to source control
- Email content sent to OpenRouter leaves the local machine — provider data retention policy should be checked before processing sensitive threads
- Consider redacting account numbers/full addresses from email bodies before LLM calls where extraction doesn't require them
- Read-only Gmail scope only — no write/delete/send capability, by design

## 4. Cost Control Mechanisms
1. Regex router eliminates ~60–70% of emails from ever reaching the LLM
2. Semantic cache prevents duplicate extraction on near-identical content
3. Tiered model selection — cheapest capable model per task
4. Batch (nightly) processing instead of real-time per-email calls
5. Local embedding model (no per-embedding API cost)

## 5. Tech Stack Summary
| Layer | Technology |
|---|---|
| Email access | Gmail API (OAuth2) |
| Router | Python regex/keyword rules |
| LLM provider | OpenRouter (multi-model gateway) |
| Structured output | Pydantic + `instructor` |
| Structured storage | SQLite → Postgres (if scaled) |
| Vector storage | Chroma → pgvector (if scaled) |
| Embeddings | `BAAI/bge-small-en-v1.5` (local) |
| Reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Caching | Redis (semantic cache) |
| Frontend | Next.js (React) + Tailwind CSS + Recharts, multi-tab dashboard |
| Backend API | FastAPI, REST endpoints per dashboard tab |
