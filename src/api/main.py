"""FastAPI main application entrypoint."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes import router
from src.config import BASE_DIR

app = FastAPI(
    title="IndexLens API",
    description="Backend REST API for IndexLens Email Intelligence Dashboard",
    version="0.1.0",
)

# Enable CORS for local Lovable / Vite / Next.js dev servers and preview URLs
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "https://lovable.dev",
        "*",  # Allow all for seamless local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import HTMLResponse

# Include API routes
app.include_router(router)

# If built frontend exists with index.html, serve it statically
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
FRONTEND_OUTPUT = BASE_DIR / "frontend" / ".output" / "public"

static_dir = None
if (FRONTEND_DIST / "index.html").exists():
    static_dir = FRONTEND_DIST
elif (FRONTEND_OUTPUT / "index.html").exists():
    static_dir = FRONTEND_OUTPUT

if static_dir:
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")
else:
    @app.get("/", response_class=HTMLResponse)
    def root():
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta http-equiv="refresh" content="0; url=http://localhost:8080/">
            <title>IndexLens — Intelligence Dashboard</title>
            <style>
                body {
                    background-color: #0d0f12;
                    color: #f1f5f9;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    margin: 0;
                }
                .card {
                    background: #181c24;
                    border: 1px solid #282f3d;
                    border-radius: 12px;
                    padding: 2.5rem;
                    text-align: center;
                    max-width: 480px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.5);
                }
                h1 { color: #f97316; margin-bottom: 0.5rem; font-size: 2rem; }
                p { color: #94a3b8; font-size: 1rem; line-height: 1.5; margin-bottom: 1.5rem; }
                a.btn {
                    display: inline-block;
                    padding: 0.8rem 1.6rem;
                    background: #f97316;
                    color: #fff;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 1rem;
                    transition: background 0.2s;
                }
                a.btn:hover { background: #ea580c; }
                .sublinks { margin-top: 1.5rem; }
                .sublinks a { color: #38bdf8; text-decoration: none; margin: 0 0.75rem; font-size: 0.9rem; }
                .sublinks a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>IndexLens</h1>
                <p>Redirecting to the live dashboard on port 8080...</p>
                <a href="http://localhost:8080/" class="btn">Open Dashboard (Port 8080)</a>
                <div class="sublinks">
                    <a href="/docs">Swagger API Docs</a>
                    <a href="/api/stats/overview">Overview Metrics</a>
                </div>
            </div>
        </body>
        </html>
        """

