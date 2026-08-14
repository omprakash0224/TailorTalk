"""
src/search_tool.py
------------------
LangChain tool that finds visually similar sarees.

Changes vs. Streamlit version:
  - Removed the Streamlit st.session_state side-effect (_push_to_session).
  - The tool now stores its last results in a module-level thread-local
    dict keyed by session_id injected via contextvars so that the FastAPI
    router can retrieve them after the agent finishes.
  - LAST_QUERY_VECTORS is now managed by backend/session_store.py.
    The tool receives session vectors via the CURRENT_SESSION_VECTORS
    contextvar and writes updated vectors back through it.
"""

from __future__ import annotations

import os
import tempfile
import uuid
import contextvars
from typing import List, Optional, Any, Dict

import requests
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from .qdrant_store import query_similar, query_with_vectors

# ---------------------------------------------------------------------------
# Context vars — set by the FastAPI router before invoking the agent so the
# tool can read/write per-request session data without global state.
# ---------------------------------------------------------------------------

# Holds {"gemini": ndarray|None, "color": ndarray|None, "gemini_border": ndarray|None}
CURRENT_SESSION_VECTORS: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "current_session_vectors",
    default={"gemini": None, "color": None, "gemini_border": None},
)

# The router reads this after the agent returns to include results in the API response
LAST_TOOL_RESULTS: contextvars.ContextVar[Optional[List[dict]]] = contextvars.ContextVar(
    "last_tool_results",
    default=None,
)

# ---------------------------------------------------------------------------
# MIME type → file extension mapping
# ---------------------------------------------------------------------------
_CONTENT_TYPE_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


# ---------------------------------------------------------------------------
# Tool schema
# ---------------------------------------------------------------------------

class SareeSearchInput(BaseModel):
    image_url: Optional[str] = Field(None, description="Public URL of the query image")
    image_path: Optional[str] = Field(None, description="Local path of the uploaded image")
    top_k: int = Field(5, description="Number of similar sarees to return, default 5")
    min_price: Optional[float] = Field(None, description="Minimum price filter in INR")
    max_price: Optional[float] = Field(None, description="Maximum price filter in INR")


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------

@tool("search_similar_sarees", args_schema=SareeSearchInput)
def search_similar_sarees(
    image_url: Optional[str] = None,
    image_path: Optional[str] = None,
    top_k: int = 5,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> List[dict]:
    """Find visually similar sarees in the catalogue given a query image.
    Use this whenever the user shares or references an image and asks for
    similar/matching/comparable items, styles, colours, or designs.
    If the user has uploaded an image, the path will be in your context, pass it to image_path."""

    session_vectors = CURRENT_SESSION_VECTORS.get()

    # -----------------------------------------------------------------------
    # No image provided — re-use cached vectors from the last search so the
    # user can apply a price filter without re-embedding the query image.
    # -----------------------------------------------------------------------
    if not image_url and not image_path:
        if session_vectors["gemini"] is not None:
            results = query_with_vectors(
                session_vectors["gemini"],
                session_vectors["color"],
                gemini_border_vec=session_vectors.get("gemini_border"),
                top_k=top_k,
                min_price=min_price,
                max_price=max_price,
            )
            dict_results = [r.model_dump() for r in results]
            LAST_TOOL_RESULTS.set(dict_results)
            return dict_results
        raise ValueError("Must provide either image_url or image_path")

    # -----------------------------------------------------------------------
    # Download URL image with correct MIME-aware extension
    # -----------------------------------------------------------------------
    temp_path = None
    try:
        if image_url:
            response = requests.get(image_url, timeout=15)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
            ext = _CONTENT_TYPE_TO_EXT.get(content_type, ".jpg")

            temp_path = os.path.join(tempfile.gettempdir(), f"query_{uuid.uuid4().hex}{ext}")
            with open(temp_path, "wb") as f:
                f.write(response.content)
            path_to_query = temp_path
        else:
            path_to_query = image_path

        results, vectors = query_similar(
            path_to_query,
            top_k=top_k,
            min_price=min_price,
            max_price=max_price,
        )

        # Persist vectors back into the contextvar so the router can store them
        CURRENT_SESSION_VECTORS.set({
            "gemini": vectors.gemini,
            "color": vectors.color,
            "gemini_border": vectors.gemini_border,
        })

        dict_results = [r.model_dump() for r in results]
        LAST_TOOL_RESULTS.set(dict_results)
        return dict_results

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
