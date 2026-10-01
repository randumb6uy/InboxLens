# IndexLens — Frontend (Lovable UI) Integration Guide

This guide walks you through integrating the React/Vite dashboard exported from [Lovable.dev](https://lovable.dev) directly into IndexLens.

---

## 1. Quick Summary of Architecture

- **Backend API**: FastAPI running on `http://localhost:8000/api` (CORS enabled for `http://localhost:5173`, `http://localhost:3000`, and `lovable.dev`).
- **Frontend App**: Vite + React + Tailwind + TypeScript in `frontend/`.
- **Pre-configured Typed Client**: `frontend/src/lib/api.ts` is already written and maps 1-to-1 with all backend endpoints and Lovable components.

---

## 2. Step-by-Step Integration

### Step 1: Export your project from Lovable
1. In Lovable.dev, generate your dashboard using the prompt provided in [`LOVABLE_PROMPT.md`](./LOVABLE_PROMPT.md).
2. Click **Export** / **Download ZIP** or sync to a GitHub repository.

### Step 2: Unpack into `frontend/`
Extract or copy the files from the Lovable export into the `frontend/` folder of this repository:
```
IndexLens/
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── pages/
│   │   └── lib/
│   │       └── api.ts   <-- (Use our pre-typed client or copy from here)
```

> **Note**: Keep or copy [`frontend/src/lib/api.ts`](./frontend/src/lib/api.ts) into your exported code. It contains the exact TypeScript interfaces and API methods for overview, financial transactions, subscriptions, newsletters, VIP contacts, schedule/meetings, and inbox sync.

### Step 3: Install Frontend Dependencies
Open a terminal in the `frontend` directory:
```bash
cd frontend
npm install
```

### Step 4: Configure the API URL
In `frontend/.env.development` (or `frontend/.env`):
```env
VITE_API_URL=http://localhost:8000/api
```

---

## 3. Connecting Components to the Backend API

`frontend/src/lib/api.ts` provides simple async methods. In your React components:

```tsx
import { useEffect, useState } from "react";
import { api, OverviewResponse, Subscription, SpendAnalytics } from "@/lib/api";

export function OverviewDashboard() {
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getOverview()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div>Loading dashboard...</div>;
  if (!data) return <div>No data found. Sync your inbox to get started.</div>;

  return (
    <div>
      <h1>Total Spend: ₹{data.metrics.total_spend_this_month}</h1>
      <p>Active Subscriptions: {data.metrics.active_subscriptions_count}</p>
      <p>VIP Senders awaiting reply: {data.metrics.vip_emails_count}</p>
    </div>
  );
}
```

### Triggering Inbox Sync from the UI:
```tsx
const handleSync = async () => {
  setIsSyncing(true);
  try {
    const result = await api.syncInbox(100, true); // true = mock data, false = real Gmail API
    alert(`Successfully synced ${result.ingested_count} emails!`);
  } catch (err) {
    console.error("Sync failed:", err);
  } finally {
    setIsSyncing(false);
  }
};
```

---

## 4. Running the Complete App

You have two options for running the app:

### Option A: Separate Dev Servers (Recommended for Development)
Terminal 1 (Backend API):
```powershell
.venv\Scripts\python -m src.cli serve --port 8000
```
Terminal 2 (Frontend with Hot Reload):
```powershell
cd frontend
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

### Option B: Single Unified Server (Production-Ready)
FastAPI automatically serves `frontend/dist` when built:
1. Build the frontend:
   ```powershell
   cd frontend
   npm run build
   cd ..
   ```
2. Start the backend:
   ```powershell
   .venv\Scripts\python -m src.cli serve --port 8000
   ```
3. Visit [http://localhost:8000](http://localhost:8000). Both API (`/api/...`) and the web dashboard UI are served from the same origin!

---

## 5. API Endpoints Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/stats/overview` | `GET` | Stat metric cards + inbox classification breakdown |
| `/api/stats/spend` | `GET` | Spend by category breakdown & recent transaction list |
| `/api/subscriptions` | `GET` | Active subscriptions with renewal dates & price hike alerts |
| `/api/newsletters` | `GET` | Detected newsletters with volume & 1-click unsubscribe URLs |
| `/api/contacts/important`| `GET`, `POST` | VIP sender list and pending correspondence |
| `/api/schedule/upcoming` | `GET` | Extracted upcoming meetings and urgent deadlines |
| `/api/jobs` | `GET` | Job-related pipeline (interviews, recruiter emails, offers) |
| `/api/inbox/sync` | `POST` | Trigger inbox fetch and deterministic classification |
| `/api/emails/{id}` | `GET` | Full raw email content & metadata for drawer view |
