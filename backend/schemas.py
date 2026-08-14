"""
backend/schemas.py
------------------
Pydantic request / response models for the TailorTalk FastAPI backend.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """JSON body for POST /api/chat (text-only variant — no image)."""
    session_id: str = Field(..., description="Client-generated UUID that identifies the conversation")
    message: str = Field(..., min_length=1, description="User's chat message")
    image_url: Optional[str] = Field(None, description="Public URL of a query image (optional)")


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class SareeResult(BaseModel):
    """A single saree match returned by the search tool."""
    sku: str
    name: str
    score: float = Field(..., description="Match percentage 0-100")
    image_url: str
    product_url: str
    price: float
    retail_price: Optional[float] = None


class ChatResponse(BaseModel):
    """Response from POST /api/chat."""
    reply: str
    results: Optional[List[SareeResult]] = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "TailorTalk"
