# Lovable Prompt: IndexLens Web Dashboard

Copy and paste the entire prompt below into [Lovable.dev](https://lovable.dev) to generate the complete frontend interface for IndexLens.

---

```markdown
Build IndexLens — an AI-powered email intelligence dashboard that connects to a user's Gmail and transforms unstructured inbox noise into clean financial analytics, subscription tracking, newsletter cleanup, important contacts, deadlines, and job opportunities.

### Overall Aesthetic & Design System
- Aesthetic: Minimal, data-dense, and calm — think Linear, Raycast, or Notion. Premium, trustworthy, and focused on clarity.
- Dark mode first (with clean light mode toggle): Background neutral slate/zinc (e.g. #0B0D11 or #0F1117), crisp white text, and subtle 1px border lines (#1F2430).
- Accent Color: Calm emerald green (e.g. #10B981) for financial metrics, paired with subtle cobalt blue (#3B82F6) and amber (#F59E0B) for alerts and deadlines. Avoid generic purple SaaS gradients.
- Typography:
  - Display/Headings: A characterful modern font (e.g. "Plus Jakarta Sans" or "Cabinet Grotesk" or a refined editorial serif like "Instrument Serif" for page titles).
  - Body & Data: Crisp, highly legible sans-serif (e.g. "Inter" or "Geist") with tabular numbers (font-mono) for all currency and metrics.
- Component Polish: Soft rounded corners (rounded-lg / 8px), subtle inset borders, zero heavy drop shadows, generous padding, and micro-interactions on hover.

### Navigation & Layout
- Persistent collapsible Left Sidebar:
  - Brand header: IndexLens logo icon + name + beta badge.
  - Navigation items with clean Lucide icons:
    1. Overview (Dashboard home)
    2. Financial & Spend
    3. Active Subscriptions
    4. Newsletters Cleaner
    5. Important Contacts (VIP)
    6. Deadlines & Meetings
    7. Job Pipeline
    8. Settings
  - Bottom of sidebar: User profile pill with connected Gmail address and a "Sync Inbox" button with spinning state on click.
- Top Header Bar:
  - Dynamic page title and breadcrumb.
  - Interactive "Ask your Inbox..." search bar with a "Cmd + K" shortcut badge (opens an AI natural language Q&A modal with suggested prompts like "How much did I spend on food this month?").
  - Date Range selector ("Last 30 Days", "This Month", "Q3 2026", "Year to Date").
  - "Last Synced: 24 mins ago" status indicator.

### Pages & Tab Sections

1. Overview Tab:
   - Metric Cards row: Total Spend This Month (with month-over-month % trend), Active Subscriptions count & monthly run-rate, Urgent Deadlines count, and VIP Emails awaiting reply.
   - Central visual: Classification donut chart showing inbox distribution (Receipts, Newsletters, Personal, Job-related, Meetings, Promos).
   - "Recent Signals" dual feed: Left column shows latest 5 financial transactions; right column shows next 3 upcoming deadlines/meetings.

2. Financial Tab:
   - Interactive charts:
     - Monthly Spend Trend (smooth line or area chart with hover tooltips).
     - Spend by Category (horizontal bar chart: Food, Travel, Cloud & Software, Utilities, Shopping).
   - Transactions Table: Filterable by category, vendor, or currency. Columns: Date, Vendor/Merchant, Category badge, Payment method, and Amount formatted in ₹ / $ with tabular numbers. Clicking a row opens the Email Detail slide-over drawer.

3. Subscriptions Tab:
   - Metrics: Total Monthly Recurring Spend, Projected Annual Cost, and Subscriptions with recent price increases.
   - Subscription Grid/Cards: Showing vendor logo/favicon placeholder, monthly/annual fee, next renewal date, active status badge, and an alert tag for price increases (e.g., "Netflix: Increased from ₹499 to ₹649").
   - Quick action: "Detect Cancellations" or "Flag for Review".

4. Newsletters Cleaner Tab:
   - Header stat: "24 newsletters detected · ~42 emails/week".
   - Clean list of newsletter senders with frequency badge (e.g. "Weekly", "Daily"), last email date, and a prominent 1-click "Unsubscribe" button (linking directly to the extracted unsubscribe URL).

5. Important Contacts (VIP) Tab:
   - Metric: Count of VIP contacts and flagged pending emails.
   - List of key relationships (e.g., Landlord, Accountant/CA, Tech Lead, Investors) showing sender email, thread subject, date received, and a status tag ("Awaiting Your Reply" vs "Replied").
   - Action to "Add New VIP Sender" via modal.

6. Deadlines & Meetings Tab:
   - Split view or toggle between Timeline view and Calendar list:
     - Meetings: Extracted meeting title, organizer, date/time, Google Meet / Zoom link button.
     - Deadlines: Bill due dates, tax filing reminders, renewal deadlines, color-coded by urgency (High / Due Soon in amber/red).

7. Job Opportunities Tab:
   - Kanban board or tagged card list tracking detected recruiting emails:
     - Columns or tags: "New Inbound", "Interview Scheduled", "Offer Received", "Closed".
     - Cards show Company name, Role title, recruiter name, and date received.

8. Settings Page:
   - Connected Gmail account management with "Disconnect" or "Re-authenticate" options.
   - VIP Contacts management table (add/remove email addresses or domains).
   - Sync preferences (Automatic Nightly Batch Sync vs Manual Sync).
   - Currency display preference (INR ₹ / USD $ / EUR €).

### Interaction Details
- Email Detail Slide-Over Drawer: Clicking any transaction, deadline, or email card smoothly slides in a right-hand drawer displaying the structured entity data alongside the raw email subject, sender, and body snippet.
- Global AI Search Modal (Cmd+K): An input asking "Ask anything about your inbox...", with quick filter chips and simulated answers referencing grounded emails.
- Realistic Mock Data: Populate with realistic personal finance and tech data (Uber, Swiggy, Amazon, AWS, GitHub, Netflix, Airtel bill, Substack newsletters, Landlord thread, Google Calendar invites).
- Responsive: Fluid layout that collapses the sidebar into a bottom or mobile drawer on smaller viewports.
```
