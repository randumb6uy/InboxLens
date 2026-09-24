"""Realistic mock email dataset for offline development, demonstrations, and test suites."""

from datetime import datetime, timedelta, timezone
from src.schemas.email_schemas import RawEmail

BASE_TIME = datetime(2026, 9, 24, 12, 0, 0, tzinfo=timezone.utc)

SAMPLE_TEMPLATES = [
    # --- RECEIPTS & BILLS (40 items) ---
    {
        "category": "receipt",
        "sender": "Uber Receipts <receipts.india@uber.com>",
        "sender_email": "receipts.india@uber.com",
        "sender_domain": "uber.com",
        "subject": "Your Wednesday morning trip with Uber",
        "body_plain": "Total: ₹342.50\nTrip Date: 2026-09-23\nPickup: Indiranagar, Bengaluru\nDrop: Koramangala 4th Block\nPayment Method: UPI\nThank you for riding with Uber.",
    },
    {
        "category": "receipt",
        "sender": "Swiggy Orders <orders@swiggy.in>",
        "sender_email": "orders@swiggy.in",
        "sender_domain": "swiggy.in",
        "subject": "Order Delivered: Meghna Foods Biryani",
        "body_plain": "Order #SW-9812401 delivered.\nVendor: Meghana Foods\nTotal Paid: ₹615.00\nItems: 1x Chicken Boneless Biryani, 1x Thums Up\nPayment: Credit Card ending in 4012.",
    },
    {
        "category": "receipt",
        "sender": "Zomato Receipts <noreply@zomato.com>",
        "sender_email": "noreply@zomato.com",
        "sender_domain": "zomato.com",
        "subject": "Your Zomato order receipt for Truffles",
        "body_plain": "Here is your invoice for order #ZOM-449102.\nRestaurant: Truffles Burgers\nSubtotal: ₹420.00\nTaxes & Fees: ₹48.00\nTotal Amount: ₹468.00\nDelivered on: 2026-09-22.",
    },
    {
        "category": "receipt",
        "sender": "Amazon.in Orders <auto-confirm@amazon.in>",
        "sender_email": "auto-confirm@amazon.in",
        "sender_domain": "amazon.in",
        "subject": "Ordered: Logitech MX Master 3S Wireless Mouse",
        "body_plain": "Order Confirmation - Order #402-8819230-1092812\nItem: Logitech MX Master 3S\nSold by: Appario Retail\nTotal: ₹7,995.00\nDelivery Date: Tomorrow by 8 PM.",
    },
    {
        "category": "receipt",
        "sender": "AWS Billing <no-reply-aws@amazon.com>",
        "sender_email": "no-reply-aws@amazon.com",
        "sender_domain": "amazon.com",
        "subject": "Amazon Web Services Invoice [Account: 8812-9901-4412]",
        "body_plain": "Greetings from Amazon Web Services.\nInvoice Summary for August 2026\nAccount: 8812-9901-4412\nTotal Charges: $48.25 (approx ₹4,050.00)\nServices: Amazon EC2, Amazon S3, Route 53.",
    },
    {
        "category": "receipt",
        "sender": "GitHub Billing <billing@github.com>",
        "sender_email": "billing@github.com",
        "sender_domain": "github.com",
        "subject": "[GitHub] Payment Receipt for GitHub Copilot Pro",
        "body_plain": "Receipt for your GitHub Copilot subscription.\nAmount: $10.00 (₹835.00)\nBilling Period: Sep 15, 2026 - Oct 15, 2026\nPayment: Visa ending in 9921.",
    },
    {
        "category": "receipt",
        "sender": "Netflix <info@mailer.netflix.com>",
        "sender_email": "info@mailer.netflix.com",
        "sender_domain": "netflix.com",
        "subject": "Your monthly Netflix membership fee",
        "body_plain": "We charged your card for your Netflix Premium plan.\nAmount: ₹649.00\nBilling Date: 2026-09-18\nNext billing date: 2026-10-18.\nManage your subscription anytime.",
    },
    {
        "category": "receipt",
        "sender": "Apple Services <no_reply@email.apple.com>",
        "sender_email": "no_reply@email.apple.com",
        "sender_domain": "apple.com",
        "subject": "Your invoice from Apple for iCloud+ 200GB",
        "body_plain": "Apple Invoice #INV-AP-994821\niCloud+ with 200GB Storage\nRenewal: ₹75.00 / month\nDate: 2026-09-17\nBilled to: Apple Pay.",
    },
    {
        "category": "receipt",
        "sender": "Spotify <no-reply@spotify.com>",
        "sender_email": "no-reply@spotify.com",
        "sender_domain": "spotify.com",
        "subject": "Your Spotify Premium Individual receipt",
        "body_plain": "Thank you for subscribing to Spotify Premium.\nPlan: Premium Individual\nAmount charged: ₹119.00\nPayment date: 2026-09-16\nEnjoy uninterrupted music.",
    },
    {
        "category": "receipt",
        "sender": "Bharti Airtel eBill <ebill@airtel.com>",
        "sender_email": "ebill@airtel.com",
        "sender_domain": "airtel.com",
        "subject": "eBill for Airtel Xstream Fiber - Account #98210948",
        "body_plain": "Dear Customer, your Airtel Broadband bill for September 2026 is ready.\nPlan: Fiber Standard 100Mbps\nBill Amount: ₹943.00\nDue Date: 2026-09-28\nPlease pay before due date to avoid late fee.",
    },

    # --- NEWSLETTERS (25 items) ---
    {
        "category": "newsletter",
        "sender": "The Pragmatic Engineer <newsletter@pragmaticengineer.com>",
        "sender_email": "newsletter@pragmaticengineer.com",
        "sender_domain": "pragmaticengineer.com",
        "subject": "Issue #184: How Big Tech builds reliable AI agent pipelines",
        "body_plain": "Welcome to this week's Pragmatic Engineer.\nToday we dissect how production teams deploy LLM tool use at scale without latency spikes.\nKey takeaways:\n1. Deterministic triage before LLM calls\n2. Structured output parsing with Pydantic\n3. Local embeddings for hybrid search.\nUnsubscribe: https://pragmaticengineer.com/unsubscribe",
    },
    {
        "category": "newsletter",
        "sender": "TLDR Tech <dan@tldr.tech>",
        "sender_email": "dan@tldr.tech",
        "sender_domain": "tldr.tech",
        "subject": "TLDR 2026-09-24: Open source models hit new milestones",
        "body_plain": "TLDR Daily Tech Briefing.\nHeadlines:\n- New reasoning models achieve parity with proprietary API endpoints.\n- Google launches next-generation Gemini developer APIs.\n- How SQLite is dominating modern edge databases.\nClick here to unsubscribe or change preferences.",
    },
    {
        "category": "newsletter",
        "sender": "ByteByteGo Newsletter <alex@bytebytego.com>",
        "sender_email": "alex@bytebytego.com",
        "sender_domain": "bytebytego.com",
        "subject": "System Design: Designing an Email Processing Agent Pipeline",
        "body_plain": "In this edition, we explore how to design high-throughput email classification and extraction engines.\nWe cover Gmail webhook vs polling, batching strategies, Redis caching, and vector stores.\nManage your subscription: https://bytebytego.com/manage",
    },

    # --- IMPORTANT / VIP CONTACTS (15 items) ---
    {
        "category": "personal",
        "sender": "Ramesh Sharma <landlord.sharma@gmail.com>",
        "sender_email": "landlord.sharma@gmail.com",
        "sender_domain": "gmail.com",
        "subject": "Apartment #402 Lease Renewal & Painting Schedule",
        "body_plain": "Hi Tushar,\nHope you are doing well.\nThe current lease agreement expires on 31st October. The landlord association decided to keep rent unchanged for the next year if you wish to renew.\nAlso, building exterior painting will start next Monday.\nPlease let me know your confirmation on the lease renewal by this Friday.\nRegards,\nRamesh Sharma",
    },
    {
        "category": "personal",
        "sender": "CA Rajesh Agarwal <ca.agarwal@gmail.com>",
        "sender_email": "ca.agarwal@gmail.com",
        "sender_domain": "gmail.com",
        "subject": "Advance Tax Q2 Computation & Form 26AS verification",
        "body_plain": "Dear Tushar,\nWe have prepared your advance tax calculation for Q2.\nPlease review the attached computation sheet. The net advance tax payable before September 30 is ₹42,500.\nKindly share the challan once payment is done so we can file the return.\nBest regards,\nRajesh Agarwal, FCA",
    },
    {
        "category": "personal",
        "sender": "Priya Nair <priya.techlead@company.io>",
        "sender_email": "priya.techlead@company.io",
        "sender_domain": "company.io",
        "subject": "Q4 Architecture Roadmap - Review & Feedback needed",
        "body_plain": "Hey Tushar,\nI have drafted the architectural design document for our indexing pipeline service.\nCould you take a look at the data flow section and leave your thoughts before our sprint sync tomorrow at 3 PM?\nLink: https://docs.company.io/arch/q4-pipeline\nThanks,\nPriya",
    },

    # --- MEETINGS & DEADLINES (10 items) ---
    {
        "category": "meeting_invite",
        "sender": "Google Calendar <calendar-notification@google.com>",
        "sender_email": "calendar-notification@google.com",
        "sender_domain": "google.com",
        "subject": "Invitation: IndexLens Architecture Sync @ Fri Sep 25, 2026 3pm - 4pm (IST)",
        "body_plain": "You have been invited to the following event:\nTitle: IndexLens Architecture Sync\nWhen: Friday Sep 25, 2026 · 3pm - 4pm (India Standard Time)\nWhere: https://meet.google.com/xyz-abcd-qrs\nOrganizer: priya.techlead@company.io\nGuests: tushar@domain.com",
    },
    {
        "category": "deadline",
        "sender": "HDFC Bank Alerts <alerts@hdfcbank.net>",
        "sender_email": "alerts@hdfcbank.net",
        "sender_domain": "hdfcbank.net",
        "subject": "Credit Card Payment Due Alert: Card ending in 4102",
        "body_plain": "Dear Customer,\nYour HDFC Bank Credit Card statement for August 2026 has been generated.\nTotal Amount Due: ₹24,810.00\nMinimum Amount Due: ₹1,500.00\nPayment Due Date: 30-Sep-2026.\nPlease pay by the due date to avoid finance charges.",
    },

    # --- PROMOTIONAL (10 items) ---
    {
        "category": "promotional",
        "sender": "MakeMyTrip Offers <promos@makemytrip.com>",
        "sender_email": "promos@makemytrip.com",
        "sender_domain": "makemytrip.com",
        "subject": "Flat 25% OFF on flights to Goa & Dubai!",
        "body_plain": "Plan your holiday now!\nGet up to ₹2,500 instant discount on domestic flights using code FLYFEST.\nValid until Sunday midnight. Terms and conditions apply.",
    },
]


def generate_mock_emails(count: int = 100) -> list[RawEmail]:
    """Generate a realistic dataset of synthetic emails for testing and offline runs."""
    emails: list[RawEmail] = []
    num_templates = len(SAMPLE_TEMPLATES)

    for i in range(count):
        tmpl = SAMPLE_TEMPLATES[i % num_templates]
        msg_id = f"msg_{1000 + i:05d}"
        thread_id = f"th_{500 + (i % 30):05d}"
        email_date = BASE_TIME - timedelta(hours=i * 3.5, minutes=(i * 17) % 60)

        # Vary subjects and bodies slightly for repeats
        multiplier = (i // num_templates) + 1
        subject = tmpl["subject"]
        body = tmpl["body_plain"]
        if multiplier > 1:
            subject = f"{subject} [Batch {multiplier}]"
            body = f"{body}\n[Reference ID: REF-{i:04d}]"

        emails.append(
            RawEmail(
                id=msg_id,
                thread_id=thread_id,
                sender=tmpl["sender"],
                sender_email=tmpl["sender_email"],
                sender_domain=tmpl["sender_domain"],
                recipient="tushar@example.com",
                subject=subject,
                date=email_date,
                snippet=body.split("\n")[0][:120],
                body_plain=body,
                body_html=f"<div>{body.replace(chr(10), '<br/>')}</div>",
                labels=["INBOX"] if i % 4 != 0 else ["INBOX", "IMPORTANT"],
            )
        )

    return emails
