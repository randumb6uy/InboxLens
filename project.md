# IndexLens — AI-Powered Gmail Data & Stats Agent

## 1. What This Is

IndexLens reads a user's Gmail inbox (via the official Gmail API, not scraping), extracts structured data from unstructured emails (receipts, bills, subscriptions, personal messages), and surfaces that data as:
- Aggregate statistics (spend by category, subscription tracking, sender/volume analytics)
- A natural-language Q&A interface over your own inbox (RAG)
- A periodic digest (weekly/monthly summary)

**Core insight this project solves:** financial and communication data already exists inside your inbox, but it's trapped as unstructured text across thousands of separate messages. Nobody manually reads and tallies hundreds of receipt emails. Sift converts that unstructured text into structured, queryable data.

## 2. Core Principle

**Deterministic-first, LLM-augmented.** Cheap regex/keyword rules handle the obvious 60–70% of emails (newsletters, known receipt formats) at zero cost. Only ambiguous emails get routed to an LLM for structured extraction. Arithmetic and aggregation (totals, averages) always run as SQL, never as LLM output — the LLM's job is extraction and natural-language synthesis, not math.

## 3. Target Users

- Personal use: individuals wanting visibility into spending/subscriptions buried in email
- Expandable later to: freelancers/small business owners doing manual expense reconciliation

## 4. Phased Roadmap

### Phase 0 — Foundations (Week 1) [DONE]
- [x] Google Cloud project + Gmail API OAuth2 setup (readonly scope)
- [x] Basic script: authenticate, list messages, fetch raw email content
- [x] Local dev environment, repo structure, `.env` for secrets
- **Exit criteria:** Can pull last 100 emails and print subject/sender/date/body to console (Completed)

### Phase 1 — Classification & Storage (Weeks 2–3) [DONE]
- [x] Regex/keyword router: classify emails into `RECEIPT`, `NEWSLETTER`, `PROMOTIONAL`, `PERSONAL`, `NEEDS_LLM`
- [x] SQLite schema for raw + classified emails
- [x] Batch ingestion job (nightly, not real-time) to control cost
- **Exit criteria:** 60–70% of a real inbox sample is classified correctly without any LLM call (Completed)

### Phase 2 — LLM Extraction Pipeline (Weeks 3–5) [DONE]
- [x] OpenRouter integration (tiered models: Gemini Flash-Lite for bulk extraction, Claude Haiku for ambiguous/anomaly cases)
- [x] Pydantic schemas for `ExtractedEmail`, `ReceiptData`, `MeetingData`, `DeadlineData`
- [x] `instructor`-based structured output calls for the `NEEDS_LLM` bucket
- [x] Redis / memory semantic cache to avoid duplicate extraction calls
- **Exit criteria:** Every classified receipt has vendor/amount/date/category extracted with reasonable accuracy on a manual spot-check (Completed)

### Phase 3 — Structured Stats & Multi-Tab React Dashboard (Weeks 5–7) [DONE]
- [x] Aggregation queries: spend by category/month, top senders, subscription detection (recurring vendor + amount pattern)
- [x] Meeting/deadline extraction: additional Pydantic schema + extraction pass for calendar-invite-style and deadline-bearing emails
- [x] Important-contacts logic: user-defined VIP list (manual add, or inferred from reply frequency/speed) used to flag and surface matching emails
- [x] React (Next.js / Vite) frontend replaces the Streamlit prototype directly — multi-tab dashboard structure & client integration:
  - **Tab: Financial Overview** — spend by category/month charts, vendor breakdown, trend over time
  - **Tab: Subscriptions** — active recurring charges, next expected renewal date, price-change flags
  - **Tab: Newsletters** — list of newsletter senders, volume received vs. opened (if open-tracking available), quick unsubscribe links
  - **Tab: Important Contacts** — recent emails from VIP senders, flagged and prioritized
  - **Tab: Meetings & Deadlines** — upcoming meetings/deadlines extracted from email content, calendar-style or list view
- [x] FastAPI backend serves aggregated data to the React frontend via REST endpoints (one per tab's data needs)
- **Exit criteria:** Dashboard answers "how much did I spend last month," "what am I still subscribed to," "what did I miss from important people," and "what's due this week" — all in one multi-tab interface (Completed)

### Phase 4 — Semantic Search & RAG Q&A (Weeks 6–8)
- [ ] Embed email bodies (`BAAI/bge-small-en-v1.5`, local CPU)
- [ ] Vector store: Chroma (simplest) or pgvector if already on Postgres
- [ ] Hybrid search (BM25 + dense, RRF) + cross-encoder reranker for precision
- [ ] Router distinguishes stats questions (→ SQL) from semantic questions (→ RAG retrieval + LLM synthesis)
- **Exit criteria:** Can ask "what did the landlord say about the deposit" and get a correct, grounded answer

### Phase 5 — Multi-Agent Layer (Weeks 8–10)
- [ ] Split into specialized agents: Extraction, Categorization, Anomaly Detection, Digest/Summarizer
- [ ] Supervisor orchestration logic (sequential + parallel steps)
- [ ] Anomaly agent: flag unusual spend spikes, new/unfamiliar senders requesting payment (phishing signal)
- [ ] Weekly digest agent: LLM-synthesized natural-language summary email/notification
- **Exit criteria:** A scheduled run produces a full weekly digest with no manual intervention

### Phase 6 — Polish & Hardening (Weeks 10–12)
- [ ] Privacy pass: redact sensitive fields before sending to OpenRouter where feasible
- [ ] Error handling, retry logic, rate-limit handling for Gmail API + OpenRouter
- [ ] Cost monitoring/alerting on OpenRouter spend
- [ ] Basic auth if deployed beyond just local personal use

## 5. Success Metrics
- % of inbox correctly classified without LLM call (cost efficiency)
- Extraction accuracy on spot-checked receipts (target: >90%)
- Time from "email arrives" to "reflected in stats" (batch cadence, e.g. nightly)
- Monthly OpenRouter spend vs. email volume (cost per 1,000 emails processed)

## 6. Dashboard Feature Set (Detail)

The dashboard is a **multi-tab React (Next.js) web app**, backed by FastAPI, with the following tabs as first-class features (not an afterthought bolted onto Phase 3 — this is now a core deliverable):

1. **Financial Statistics** — total spend, spend by category, spend by vendor, month-over-month trend, largest transactions
2. **Active Subscriptions** — detected recurring charges, renewal cadence, next expected charge date, price-increase alerts
3. **Newsletters** — all detected newsletter senders, frequency received, one-click reference to unsubscribe links found in email bodies
4. **Important Contacts** — emails from a user-defined (or inferred) VIP list, surfaced separately from the general inbox noise, with reply-status indicators
5. **Meetings & Deadlines** — extracted meeting invites and deadline-bearing emails (e.g. "submit by," "due on," "deadline"), shown as an upcoming list or simple calendar view

Each tab is backed by its own structured query/extraction path — see `architecture.md` for the schema and API design.

## 7. Key Risks / Open Questions
- **Privacy:** email content leaves the machine once routed to OpenRouter — needs explicit user awareness/consent, especially for sensitive threads
- **Extraction accuracy on messy/unusual formats** — vendor email templates vary wildly; may need per-vendor few-shot examples over time
- **Gmail API rate limits** at high email volume — batch job needs to respect quotas
- **Subscription/recurrence detection** is a heuristic (same vendor + similar amount + monthly interval) — will need tuning against false positives

## 8. See Also
Technical stack, data flow, and schemas are documented in `architecture.md`.
