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

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

app.include_router(chat_router)

# ---------------------------------------------------------------------------
# Serve the compiled React frontend (production only)
# ---------------------------------------------------------------------------
# The Dockerfile builds frontend/ → frontend/dist/ and the image places that
# at /app/frontend/dist.  We only mount it if the directory exists so that
# `uvicorn backend.main:app --reload` still works during local development
# without needing to build the frontend first.

_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    # Serve static assets (JS bundles, CSS, images, etc.)
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        """Catch-all route that returns index.html for client-side routing."""
        index = _FRONTEND_DIST / "index.html"
        return FileResponse(str(index))
