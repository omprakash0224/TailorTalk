# Architecture & Technical Decisions

This document outlines the technical decisions, model choices, database architecture, framework migrations, search quality enhancements, and associated assumptions/trade-offs in the TailorTalk Visual Saree Search platform.

---

## 1. Model & Embedding Choices

### Conversational LLM (Agent Reasoning)
*   **Model:** `llama-3.3-70b-versatile` via **Groq**.
*   **Purpose:** Powers the conversational LangGraph ReAct agent. It performs intent recognition, parses user constraints (e.g., price limits), decides when to trigger visual vector search, and composes natural language summaries.
*   **Why Groq:** Groq's LPU inference engine delivers ultra-low latency (< 1s time-to-first-token), keeping the chat interface responsive during multi-turn shopping conversations.

### Multimodal Semantic Embeddings
*   **Model:** `models/gemini-embedding-2-preview` via **Google GenAI** (`google-genai` SDK).
*   **Dimensionality:** 3072-dimensional vector, L2-normalized.
*   **Task Type Discipline:**
    *   `RETRIEVAL_DOCUMENT`: Used when indexing catalog sarees (`scripts/build_index.py`).
    *   `RETRIEVAL_QUERY`: Used for live user query images and border crops (`src/embeddings.py`, `src/qdrant_store.py`).
*   **Why:** Gemini 2.0 provides state-of-the-art visual semantic understanding across fabric textures, drape, weave intricacies, and aesthetic motifs. Maintaining task type asymmetry ensures optimal cosine distance calculations in vector space.

### Deterministic Color Embeddings
*   **Algorithm:** HSV Color Histogram via **OpenCV**.
*   **Dimensionality:** 96-dimensional vector (32 bins per channel H, S, V), L2-normalized.
*   **Why:** Deep multimodal neural embeddings sometimes emphasize high-level structure over exact color hues. In ethnic fashion, exact color match is critical for shoppers. Computing a deterministic HSV histogram guarantees color fidelity and prevents color drift.

---

## 2. Vector Database Architecture

*   **Database:** **Qdrant** (Cloud / Docker / Memory).
*   **Collection:** `sarees` with named vectors:
    *   `gemini`: 3072-dimensional vector, Cosine distance.
    *   `color`: 96-dimensional vector, Cosine distance.
*   **Search Strategy:** 3-stream Prefetch + **Reciprocal Rank Fusion (RRF)**:
    1.  Prefetch on `gemini` using full-image query vector (`RETRIEVAL_QUERY`).
    2.  Prefetch on `color` using HSV histogram vector.
    3.  Prefetch on `gemini` using border/pallu crop query vector (`RETRIEVAL_QUERY`).
*   **Payload Filtering:** In-database payload filtering on `discounted_price` using `FieldCondition` and `Range(gte=min_price, lte=max_price)` pushed directly into Qdrant prefetch queries.

---

## 3. Framework & System Architecture

TailorTalk employs a decoupled, production-grade **FastAPI + React 18 SPA** architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    React 18 SPA Frontend                    │
│  - Image Studio Sidebar (Drag-and-Drop / URL / Prompts)     │
│  - Chat Window (Markdown Messages / Typing Indicators)      │
│  - Interactive ProductGrid & ProductCard Components         │
│  - useChat Hook (Session UUID & Message Lifecycle)          │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP POST /api/chat (multipart)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       FastAPI Backend                       │
│  - main.py (App Factory, CORS, Static SPA Fallback Mount)   │
│  - routers/chat.py (POST /api/chat, GET /api/health)        │
│  - schemas.py (Pydantic Models: ChatResponse, SareeResult)  │
│  - session_store.py (Thread-safe TTL Store & Eviction)      │
│  - ContextVars for Request-Scoped Vector & Result Passing   │
│  - Threadpool Executor for Async Agent Execution            │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
               ▼                               ▼
┌──────────────────────────────┐ ┌────────────────────────────┐
│      LangGraph ReAct Agent   │ │      Qdrant Vector DB      │
│  - Groq LLaMA-3.3-70b        │ │  - Collection: 'sarees'    │
│  - Tool: search_similar_     │ │  - 3-Signal Prefetch + RRF │
│    sarees                    │ │  - Price Range Filtering   │
└──────────────────────────────┘ └────────────────────────────┘
```

### Backend Components (`backend/`)
1.  **FastAPI Core (`backend/main.py`):** Configures CORS for local development (port 5173/8000), includes chat routers, and mounts the compiled React distribution (`frontend/dist`) at `/` with SPA catch-all routing for production single-origin hosting.
2.  **Chat Router (`backend/routers/chat.py`):** Handles `POST /api/chat` supporting `multipart/form-data` for text messages combined with image files or URLs. Dispatches synchronous agent operations into an asynchronous thread-pool executor (`_run_agent_async`).
3.  **Thread-Safe Session Store (`backend/session_store.py`):**
    *   Replaces legacy Streamlit session state with an in-memory, mutex-guarded session store.
    *   Holds: Agent instance, multi-turn LangChain chat history, and cached query vectors (`gemini`, `color`, `gemini_border`).
    *   Lifecycle limits: `MAX_SESSIONS = 200`, `SESSION_TTL = 3600s` (1 hour) with automatic stale eviction and least-recently-seen eviction at capacity.
4.  **Request ContextVars:** Employs `contextvars.ContextVar` (`CURRENT_SESSION_VECTORS`, `LAST_TOOL_RESULTS`) to safely pass session vectors and capture tool outputs during concurrent request handling without global state collisions.

### Frontend Components (`frontend/`)
1.  **React 18 + Vite SPA:** Fast, modern client interface with hot module reloading and optimized production bundling.
2.  **Image Studio Sidebar (`ImageUploadSidebar.jsx`):** Dedicated panel for drag-and-drop file upload, URL input, query image preview, and contextual quick prompt chips.
3.  **Chat Window & Message Bubbles (`ChatWindow.jsx`, `MessageBubble.jsx`):** Supports markdown formatting, conversational styling, error handling, and animated typing indicators.
4.  **Product Grid & Cards (`ProductGrid.jsx`, `ProductCard.jsx`):** Displays retrieved saree matches with match score badges, price comparison (with retail price strikethrough), and direct store links.
5.  **Session Hook (`hooks/useChat.js`):** Manages client session UUID, multi-turn state persistence, and communication with `/api/chat`.

### Deployment & Packaging
*   **Multi-Stage Dockerfile:**
    *   `Stage 1a (py-builder)`: Installs and compiles Python wheels.
    *   `Stage 1b (frontend-builder)`: Installs Node dependencies and compiles Vite frontend into `frontend/dist`.
    *   `Stage 2 (runtime)`: Debian slim runtime with OpenCV shared libraries (`libgl1`, `libglib2.0-0`, `curl`), exposing port 8000 and serving the unified SPA + API.
*   **Render Infrastructure (`render.yaml`):** Infrastructure-as-Code specification for deploying the Docker container with automatic health check monitoring at `/api/health`.

### Prototyping Runner
*   **Streamlit (`app.py`):** Maintained as an alternative rapid-prototyping runner featuring an embedded daemon HTTP server (`_HealthHandler` on port 8502) for isolated health probes.

---

## 4. Search Quality & Retrieval Enhancements

1.  **3-Signal Multi-Vector Search & RRF:** Combines full-image Gemini embeddings, HSV color histograms, and border/pallu crop Gemini embeddings via Qdrant Reciprocal Rank Fusion.
2.  **Asymmetric Task Types:** Enforces `RETRIEVAL_DOCUMENT` during indexing and `RETRIEVAL_QUERY` during search to preserve vector projection fidelity.
3.  **L2 Normalization:** Strictly normalizes all vectors before insertion and similarity querying.
4.  **Session-Isolated Vector Caching:** Caches query vectors per session, allowing zero-latency follow-up queries (e.g., *"show me options under ₹3,500"*) that execute in-database price filtering directly without re-embedding images.
5.  **Score Normalization (`_rrf_to_pct`):** Maps raw RRF scores into transparent 0–100% "Match %" metrics relative to the best candidate.
6.  **Rate-Limit Resilience:** Implements exponential backoff retry handling for Gemini API calls to maintain stability under high traffic.

---

## 5. Assumptions and Trade-offs

1.  **In-Memory Session Store vs. Distributed Cache:**
    *   *Assumption:* The deployment runs as a single container instance (e.g., standard Render / Docker service).
    *   *Decision:* An in-memory store with mutex locking, TTL, and LRU eviction avoids external dependencies like Redis while keeping per-session latency negligible.
    *   *Trade-off:* If horizontally scaling across multiple container replicas, the session store would need to be migrated to Redis.
2.  **Decoupled Structured Results vs. LLM Context Window:**
    *   *Decision:* The LLM returns a conversational summary text, while raw product match structures are returned separately in `ChatResponse.results` for client-side React rendering.
    *   *Trade-off:* Minimizes token usage, prevents LLM hallucination in product links/prices, and speeds up inference, but means the LLM does not perform reasoning on the full JSON metadata of every match.
3.  **Multi-Vector Storage Footprint vs. Visual Fidelity:**
    *   *Trade-off:* Storing two named vectors (`gemini` 3072-dim and `color` 96-dim) per catalog item increases vector database storage compared to single-vector setups. This is accepted in return for significantly higher retrieval accuracy.
4.  **Unified Single-Origin Container Serving:**
    *   *Decision:* The FastAPI backend serves the compiled React SPA from `frontend/dist` in production.
    *   *Trade-off:* Eliminates CORS complexity and hosting costs for a separate frontend server, though a dedicated CDN would be preferred for high-scale enterprise deployments.
