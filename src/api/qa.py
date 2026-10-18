"""Natural language question answering agent grounded in local SQLite data and LLM synthesis."""

import logging
from typing import Any, Optional
from openai import OpenAI

from src.config import (
    EXTRACTION_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
)
from src.storage.db import Database

logger = logging.getLogger(__name__)


def answer_inbox_question(
    query: str,
    db: Optional[Database] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> dict[str, Any]:
    """Answer a user query by retrieving relevant SQLite context and synthesizing via LLM."""
    db = db or Database()
    api_key = api_key if api_key is not None else OPENROUTER_API_KEY
    base_url = base_url or OPENROUTER_BASE_URL
    model = model or EXTRACTION_MODEL

    clean_query = query.strip()
    if not clean_query:
        return {
            "query": query,
            "answer": "Please ask a question about your spending, subscriptions, meetings, or emails.",
            "sources": [],
        }

    # 1. Retrieve structured context from local database
    metrics = db.get_overview_metrics()
    subs = db.list_subscriptions()
    sched = db.list_upcoming_schedule()
    spend = db.get_spend_analytics()
    matching_emails = db.search_emails(clean_query, limit=5)

    # Format context pieces
    total_spend = metrics.get("total_spend_this_month", 0)
    currency = metrics.get("currency", "INR")
    curr_sym = "₹" if currency == "INR" else ("$" if currency == "USD" else currency)

    categories_summary = ", ".join(
        [f"{c['category']}: {curr_sym}{c['total']:.2f}" for c in spend.get("categories", [])[:5]]
    ) or "None recorded"

    top_txs = ", ".join(
        [
            f"{t['vendor']} ({curr_sym}{t['amount']} on {t.get('date', 'recent')})"
            for t in spend.get("transactions", [])[:6]
        ]
    ) or "None"

    subs_summary = ", ".join(
        [
            f"{s['vendor']} ({curr_sym}{s['last_amount']}/{s.get('cadence', 'mo')}, next: {s.get('next_expected_date', 'soon')})"
            for s in subs[:8]
        ]
    ) or "No active subscriptions detected"

    meetings_summary = ", ".join(
        [f"{m['title']} ({m.get('datetime_start', '')[:10]})" for m in sched.get("meetings", [])[:5]]
    ) or "No meetings scheduled"

    deadlines_summary = ", ".join(
        [f"{d['description']} (Due: {d.get('due_date', 'soon')})" for d in sched.get("deadlines", [])[:5]]
    ) or "No upcoming deadlines"

    email_snippets = []
    sources = []
    for em in matching_emails:
        sources.append(f"{em.get('sender', 'Unknown')}: {em.get('subject', 'Untitled')}")
        snippet_text = em.get("snippet") or em.get("subject") or ""
        email_snippets.append(
            f"- [{em.get('date', '')[:10]}] From: {em.get('sender')} | Subject: {em.get('subject')} | Context: {snippet_text}"
        )
    emails_text = "\n".join(email_snippets) if email_snippets else "No direct matching emails found."

    context_prompt = (
        f"FACTUAL CONTEXT FROM USER'S INBOX & DATABASE:\n"
        f"- Total Month Spend: {curr_sym}{total_spend:.2f}\n"
        f"- Spend by Category: {categories_summary}\n"
        f"- Recent Transactions: {top_txs}\n"
        f"- Active Subscriptions ({len(subs)}): {subs_summary}\n"
        f"- Upcoming Meetings: {meetings_summary}\n"
        f"- Upcoming Deadlines / Bills: {deadlines_summary}\n\n"
        f"RELEVANT EMAILS FOUND:\n{emails_text}\n"
    )

    system_prompt = (
        "You are IndexLens AI, a personal intelligence assistant for the user's Gmail inbox and finances. "
        "Answer the user's question accurately, concisely (1 to 3 sentences), and politely based strictly on the provided context. "
        "Cite specific numbers, dates, amounts, and sender names when relevant. "
        "If the information is not in the context, clearly state that it was not found in the indexed messages."
    )

    # 2. Attempt LLM generation
    if (
        api_key
        and api_key.strip()
        and api_key != "your_openrouter_api_key_here"
        and not api_key.lower().startswith("mock")
    ):
        models_to_try = [
            model,
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
            "liquid/lfm-2.5-2.6b:free",
        ]
        for m in models_to_try:
            try:
                client = OpenAI(
                    base_url=base_url,
                    api_key=api_key,
                    timeout=10.0,
                    default_headers={
                        "HTTP-Referer": "https://github.com/indexlens/indexlens",
                        "X-Title": "IndexLens",
                    },
                )
                resp = client.chat.completions.create(
                    model=m,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"{context_prompt}\nUser Question: {clean_query}"},
                    ],
                    temperature=0.1,
                    max_tokens=250,
                )
                if not resp.choices or not resp.choices[0].message:
                    continue
                raw_content = resp.choices[0].message.content or ""
                answer = raw_content.strip()
                if answer:
                    return {
                        "query": query,
                        "answer": answer,
                        "sources": sources[:4],
                        "model": m,
                    }
            except Exception as err:
                logger.warning("QA LLM failed with %s: %s. Trying next candidate...", m, err)

    # 3. Deterministic Heuristic Fallback Answer (offline or API limit)
    q_lower = clean_query.lower()
    if any(w in q_lower for w in ["spend", "money", "cost", "total", "food", "paid"]):
        answer = (
            f"Your tracked spend is {curr_sym}{total_spend:.2f} across "
            f"{len(spend.get('transactions', []))} transactions. Categories: {categories_summary}."
        )
    elif any(w in q_lower for w in ["subscription", "recurring", "renew"]):
        answer = (
            f"You have {len(subs)} active subscriptions: {subs_summary}."
        )
    elif any(w in q_lower for w in ["deadline", "due", "bill", "meeting", "schedule", "calendar"]):
        answer = (
            f"Meetings: {meetings_summary}. Deadlines & Bills: {deadlines_summary}."
        )
    elif matching_emails:
        top_m = matching_emails[0]
        answer = (
            f"Found relevant email from {top_m.get('sender')}: \"{top_m.get('subject')}\" "
            f"({top_m.get('snippet', '')[:100]})."
        )
    else:
        answer = (
            f"Indexed {metrics.get('total_emails', 100)} emails in SQLite. "
            f"You can ask about monthly spend ({curr_sym}{total_spend:.2f}), active subscriptions, deadlines, or specific senders."
        )

    return {
        "query": query,
        "answer": answer,
        "sources": sources[:4],
        "model": "heuristic-fallback",
    }
