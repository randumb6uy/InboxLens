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

# Include API routes
app.include_router(router)

# If Lovable built frontend exists in frontend/dist, serve it statically
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
