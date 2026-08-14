"""
backend/routers/chat.py
-----------------------
FastAPI router handling:
  POST /api/chat  — text message (+ optional image URL or uploaded file)
  GET  /api/health — liveness probe
"""

from __future__ import annotations

import os
import tempfile
import uuid
import copy

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from langchain_core.messages import HumanMessage, AIMessage

from backend.schemas import ChatResponse, HealthResponse, SareeResult
from backend import session_store
from src.search_tool import CURRENT_SESSION_VECTORS, LAST_TOOL_RESULTS

router = APIRouter()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


# ---------------------------------------------------------------------------
# Chat — text only (JSON body)
# ---------------------------------------------------------------------------

@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    session_id: str = Form(...),
    message: str = Form(...),
    image_url: str = Form(None),
    image: UploadFile = File(None),
) -> ChatResponse:
    """
    Accepts multipart/form-data so the frontend can attach an image file in
    the same request as the text message.

    Flow:
      1. Retrieve (or create) the session.
      2. Set contextvars so the search tool can read/write per-session vectors.
      3. Build the agent prompt (injecting image path/URL as needed).
      4. Run the agent.
      5. Harvest tool results + updated vectors from contextvars.
      6. Persist updated vectors back to the session store.
      7. Return the assistant reply + optional saree results.
    """
    session = session_store.get_or_create(session_id)

    # -----------------------------------------------------------------------
    # Save uploaded image to a temp file (if provided)
    # -----------------------------------------------------------------------
    temp_image_path: str | None = None
    try:
        if image and image.filename:
            ext = os.path.splitext(image.filename)[1] or ".jpg"
            temp_image_path = os.path.join(tempfile.gettempdir(), f"upload_{uuid.uuid4().hex}{ext}")
            content = await image.read()
            with open(temp_image_path, "wb") as f:
                f.write(content)

        # -----------------------------------------------------------------------
        # Build agent input — append image context hint so the LLM knows to
        # call the search tool with the right argument.
        # -----------------------------------------------------------------------
        agent_input = message

        if temp_image_path:
            agent_input += (
                f"\n[User uploaded an image. Local path: {temp_image_path}. "
                "Use this path for the image_path argument of search_similar_sarees.]"
            )
        elif image_url:
            agent_input += (
                f"\n[User provided an image URL: {image_url}. "
                "Use this for the image_url argument of search_similar_sarees.]"
            )

        # -----------------------------------------------------------------------
        # Set contextvars for this request's execution context
        # -----------------------------------------------------------------------
        vectors_token = CURRENT_SESSION_VECTORS.set(
            copy.deepcopy(session["last_vectors"])
        )
        results_token = LAST_TOOL_RESULTS.set(None)

        # -----------------------------------------------------------------------
        # Run the LangGraph agent (synchronous — runs in the default executor)
        # -----------------------------------------------------------------------
        from src.agent import run_agent  # local import avoids circular import at startup

        reply = await _run_agent_async(session, agent_input)

        # -----------------------------------------------------------------------
        # Harvest results and updated vectors from contextvars
        # -----------------------------------------------------------------------
        tool_results: list[dict] | None = LAST_TOOL_RESULTS.get()
        updated_vectors = CURRENT_SESSION_VECTORS.get()

        # Reset contextvars
        CURRENT_SESSION_VECTORS.reset(vectors_token)
        LAST_TOOL_RESULTS.reset(results_token)

        # -----------------------------------------------------------------------
        # Update session: chat history + cached vectors
        # -----------------------------------------------------------------------
        session["chat_history"].append(HumanMessage(content=agent_input))
        session["chat_history"].append(AIMessage(content=reply))

        if updated_vectors.get("gemini") is not None:
            session_store.update_vectors(
                session_id,
                updated_vectors["gemini"],
                updated_vectors["color"],
                updated_vectors.get("gemini_border"),
            )

        # -----------------------------------------------------------------------
        # Build response
        # -----------------------------------------------------------------------
        saree_results = None
        if tool_results:
            saree_results = [
                SareeResult(
                    sku=r.get("sku", ""),
                    name=r.get("name", ""),
                    score=r.get("score", 0.0),
                    image_url=r.get("image_url", ""),
                    product_url=r.get("product_url", ""),
                    price=r.get("price", 0.0),
                    retail_price=r.get("retail_price"),
                )
                for r in tool_results
            ]

        return ChatResponse(reply=reply, results=saree_results)

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    finally:
        # Clean up temp upload file
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.remove(temp_image_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Helper: run blocking agent in threadpool so we don't block the event loop
# ---------------------------------------------------------------------------

import asyncio


async def _run_agent_async(session: dict, agent_input: str) -> str:
    """Run the synchronous LangGraph agent in a thread-pool executor."""
    loop = asyncio.get_event_loop()
    from src.agent import run_agent

    reply = await loop.run_in_executor(
        None,
        lambda: run_agent(session["agent"], agent_input, session["chat_history"]),
    )
    return reply
