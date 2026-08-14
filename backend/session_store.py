"""
backend/session_store.py
------------------------
Thread-safe, in-memory per-session store that replaces Streamlit's
st.session_state for the FastAPI deployment.

Each session entry holds:
  - agent          : LangGraph ReAct agent instance
  - chat_history   : list of LangChain message objects for multi-turn context
  - last_vectors   : dict of {"gemini", "color", "gemini_border"} numpy arrays
                     cached from the most recent image search so the user can
                     apply price filters without re-embedding the query image.
  - last_seen      : float timestamp — used by the sweeper to evict stale sessions

Limits
------
MAX_SESSIONS : hard cap on number of live sessions (oldest evicted when exceeded)
SESSION_TTL  : sessions inactive for this many seconds are eligible for eviction
"""

from __future__ import annotations

import time
import threading
from typing import Dict, Any, Optional

import numpy as np

MAX_SESSIONS: int = 200
SESSION_TTL: float = 3600.0  # 1 hour

_store: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _evict_stale() -> None:
    """Remove sessions that have exceeded TTL. Call this before writes."""
    now = time.monotonic()
    stale = [sid for sid, s in _store.items() if now - s["last_seen"] > SESSION_TTL]
    for sid in stale:
        del _store[sid]


def _evict_oldest() -> None:
    """When at capacity, drop the least-recently-seen session."""
    if not _store:
        return
    oldest = min(_store, key=lambda sid: _store[sid]["last_seen"])
    del _store[oldest]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_or_create(session_id: str) -> Dict[str, Any]:
    """
    Return the session dict for *session_id*, creating it if it doesn't exist.
    Lazily imports and constructs the agent on first access to avoid startup cost.
    """
    with _lock:
        _evict_stale()

        if session_id not in _store:
            if len(_store) >= MAX_SESSIONS:
                _evict_oldest()

            from src.agent import create_agent  # lazy import — avoids circular deps at module load

            _store[session_id] = {
                "agent": create_agent(),
                "chat_history": [],
                "last_vectors": {"gemini": None, "color": None, "gemini_border": None},
                "last_seen": time.monotonic(),
            }
        else:
            _store[session_id]["last_seen"] = time.monotonic()

        return _store[session_id]


def get(session_id: str) -> Optional[Dict[str, Any]]:
    """Return the session dict or None if the session doesn't exist."""
    with _lock:
        session = _store.get(session_id)
        if session:
            session["last_seen"] = time.monotonic()
        return session


def update_vectors(
    session_id: str,
    gemini: np.ndarray,
    color: np.ndarray,
    gemini_border: Optional[np.ndarray],
) -> None:
    """Persist the latest query vectors for a session (price-filter re-use)."""
    with _lock:
        session = _store.get(session_id)
        if session:
            session["last_vectors"] = {
                "gemini": gemini,
                "color": color,
                "gemini_border": gemini_border,
            }
            session["last_seen"] = time.monotonic()


def get_vectors(session_id: str) -> Dict[str, Any]:
    """Return the cached query vectors for a session."""
    with _lock:
        session = _store.get(session_id)
        if session:
            return session["last_vectors"]
        return {"gemini": None, "color": None, "gemini_border": None}
