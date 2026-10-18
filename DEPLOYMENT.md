# IndexLens — Deployment & Launch Guide

This guide details all options to launch, run, and deploy IndexLens — from 1-click local execution to containerized Docker workflows and production cloud infrastructure.

---

## Architecture Quick Reference

| Component | Technology | Default Port / Target | Purpose |
|---|---|---|---|
| **Backend API** | FastAPI, Uvicorn, SQLite | `8000` | REST API, email classification, entity extraction, RAG |
| **Frontend UI** | Vite, React 19, TanStack Start | `8080` (or `5173` via forwarder) | Black & orange intelligence dashboard |
| **Forwarder Proxy** | Node.js | `5173` -> `8080` | Ensures standard Vite URLs redirect seamlessly |

---

## Option 1: One-Click Local Full-Stack Launch (Recommended for Dev & Demo)

Start the backend API, frontend dashboard, and port forwarder concurrently with a single command, automatically opening your browser:

### Using PowerShell:
```powershell
.\launch.ps1
```

### Using Command Prompt / Double-Click:
```cmd
launch.bat
```

### Using Python CLI directly:
```powershell
.venv\Scripts\python -m src.cli launch
```

> **Note**: Press `Ctrl+C` in the terminal to cleanly shut down all services simultaneously.

---

## Option 2: Docker / Containerized Launch (Recommended for Self-Hosting)

Run both the FastAPI backend and React frontend in isolated containers:

### Prerequisites:
- [Docker Desktop](https://www.docker.com/) installed and running.

### 1. Build and Run:
```bash
docker compose up --build
```

### 2. Access:
- **Dashboard UI**: `http://localhost:8080`
- **Backend API & Swagger Docs**: `http://localhost:8000/docs`

---

## Option 3: Production Cloud Deployment

Deploy IndexLens to public cloud services for 24/7 access.

### A. Deploy Frontend to Cloudflare Pages (Free & Edge-Accelerated)

The frontend is pre-configured with `@lovable.dev/vite-tanstack-config` and built with Cloudflare Pages/Workers as its native target:

1. **Build frontend assets**:
   ```bash
   cd frontend
   npm run build
   ```
2. **Deploy with Wrangler**:
   ```bash
   npx wrangler pages deploy .output/public --project-name=indexlens
   ```
3. Set the environment variable in Cloudflare Dashboard:
   - `VITE_API_URL` = `https://api.yourdomain.com/api` (or your backend URL below).

*(Alternatively, connect your GitHub repository directly to Cloudflare Pages or Vercel).*

---

### B. Deploy Backend to Render, Railway, or Google Cloud Run

The backend is packaged as a standard containerized FastAPI application (`Dockerfile`).

#### 1. Deploy to Render (1-Click from GitHub)
1. Go to [Render Dashboard](https://dashboard.render.com/) -> **New Web Service**.
2. Connect your GitHub repository (`InboxLens`).
3. Select **Docker** environment.
4. Set environment variables:
   - `OPENROUTER_API_KEY`: `sk-or-v1-...`
   - `MOCK_GMAIL`: `false` (or `true` if testing without live Google credentials).
5. Add a persistent disk if using SQLite (`/app/indexlens.db`), or configure Supabase Postgres in `.env`.

#### 2. Deploy to Google Cloud Run (Serverless Container)
```bash
gcloud run deploy indexlens-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENROUTER_API_KEY="sk-or-v1-..."
```

---

## Option 4: Desktop Application Wrapper (Tauri / PyWebview)

For users who want a native `.exe` desktop application without opening browsers or terminals:

### Quick PyWebview Launch:
```python
import webview
import subprocess
import sys

# Start backend in background
backend = subprocess.Popen([sys.executable, "-m", "src.cli", "serve", "--port", "8000"])

# Open native OS desktop window
webview.create_window("IndexLens", "http://localhost:8080", width=1280, height=840)
webview.start()

backend.terminate()
```

---

## Production Security & Gmail OAuth Checklist

Before going live with external users:
- [ ] In [Google Cloud Console](https://console.cloud.google.com/), submit your OAuth consent screen for verification if publishing outside test users.
- [ ] Configure `ALLOWED_ORIGINS` in `src/api/main.py` with your production frontend domain (e.g., `https://indexlens.pages.dev`).
- [ ] Secure your `.env` file and never commit `credentials.json` or `token.json` to public repositories.
