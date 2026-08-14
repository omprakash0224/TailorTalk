"""
backend/main.py
---------------
FastAPI application entry point for TailorTalk.

In production the React build is served as static files mounted at '/',
so both the API and the frontend are served from the same origin
(no CORS issues, single Docker port).

In development:
  - Run the backend: uvicorn backend.main:app --reload --port 8000
  - Run the frontend: cd frontend && npm run dev   (proxies /api/* to :8000)
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.routers.chat import router as chat_router

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="TailorTalk API",
    description="Visual saree search powered by Gemini embeddings + Qdrant + LangGraph",
    version="2.0.0",
)

# ---------------------------------------------------------------------------
# CORS — allow the Vite dev server (port 5173) during development.
# In production, both frontend and backend are on the same origin so CORS
# is not strictly needed, but we keep it for flexibility.
# ---------------------------------------------------------------------------

_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:4173",  # Vite preview
    "http://localhost:8000",  # uvicorn dev
]

if os.getenv("FRONTEND_URL"):
    _ALLOWED_ORIGINS.append(os.getenv("FRONTEND_URL"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",  # Allow Vercel preview environments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

app.include_router(chat_router)

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint to keep the server awake and check dependencies."""
    qdrant_configured = bool(os.getenv("QDRANT_URL") and os.getenv("QDRANT_API_KEY"))
    gemini_configured = bool(os.getenv("GEMINI_API_KEY"))
    groq_configured = bool(os.getenv("GROQ_API_KEY"))
    
    is_healthy = qdrant_configured and gemini_configured and groq_configured
    
    return {
        "status": "ok" if is_healthy else "degraded",
        "dependencies": {
            "qdrant": "configured" if qdrant_configured else "missing",
            "gemini": "configured" if gemini_configured else "missing",
            "groq": "configured" if groq_configured else "missing"
        }
    }

@app.get("/", tags=["Info"])
async def api_info():
    """Basic endpoint to provide API information."""
    return {
        "name": "TailorTalk API Server",
        "version": "2.0.0",
        "status": "online",
        "docs_url": "/docs"
    }
