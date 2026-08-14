# TailorTalk Flow Documentation

This document outlines the architecture, pipelines, and data flows in the TailorTalk Visual Saree Search project. It details the catalog ingestion and indexing pipeline, the FastAPI and LangGraph ReAct agent request pipeline, and the end-to-end user interaction flow.

---

## 1. Ingestion / Indexing Pipeline

The indexing pipeline processes the saree product catalog, extracts multi-modal and color feature representations, and stores them in a Qdrant vector database for fast similarity retrieval.

**Key Steps:**
1. **Catalog Loading & Deduplication:** Reads product metadata from `data/byrappa_tejas_31july.csv`, strips whitespace, drops invalid rows, and deduplicates by `image_url`.
2. **Resumable Progress Tracking:** Checks `data/index_progress.log` to skip already indexed SKUs, enabling robust restarts without redundant API calls.
3. **Feature Extraction (per saree image `data/images/{sku}.jpg`):**
   - **Semantic Embedding (Gemini):** Computes a 3072-dimensional vector using Google GenAI `models/gemini-embedding-2-preview` with the `RETRIEVAL_DOCUMENT` task type, followed by L2 normalization.
   - **Color Histogram (OpenCV):** Computes a 96-dimensional vector representing the HSV color distribution (3 channels × 32 bins), L2-normalized.
4. **Vector Database Ingestion:**
   - Generates deterministic point IDs using UUIDv5 derived from the SKU (`uuid.uuid5(uuid.NAMESPACE_OID, sku)`).
   - Batches points (chunk size = 100) and upserts them into the Qdrant `sarees` collection with named vectors (`gemini`, `color`) and metadata payload (`sku`, `name`, `retail_price`, `discounted_price`, `image_url`, `product_url`, `in_stock`).
   - Appends processed SKUs to `index_progress.log`.

```mermaid
flowchart TD
    A["Start Indexing Script<br/>scripts/build_index.py"] --> B["Connect to Qdrant"]
    B --> C{"Collection 'sarees' exists?"}
    C -->|No| D["Create 'sarees' collection<br/>- gemini: 3072 dim, Cosine<br/>- color: 96 dim, Cosine"]
    C -->|Yes| E["Load CSV Catalog"]
    D --> E
    E --> F["Load processed SKUs from log"]
    
    F --> G{"For each SKU in CSV"}
    G -->|Already Processed?| H["Skip"]
    G -->|New SKU?| I{"Image Exists locally?"}
    I -->|No| H
    I -->|Yes| J["Extract Features"]
    
    subgraph Feature_Extraction ["Feature Extraction"]
        J --> K["Gemini API: embed_image_gemini<br/>task_type: RETRIEVAL_DOCUMENT"]
        K --> L["3072-dim L2-normalized Vector"]
        J --> M["OpenCV: compute_color_histogram<br/>HSV 32 bins x 3"]
        M --> N["96-dim L2-normalized Vector"]
    end
    
    L --> O["Create PointStruct<br/>ID: UUIDv5(SKU)<br/>Payload: metadata + pricing"]
    N --> O
    
    O --> P{"Batch size >= 100?"}
    P -->|No| G
    P -->|Yes| Q["Upsert Batch to Qdrant"]
    Q --> R["Append SKUs to index_progress.log"]
    R --> G
    
    G -->|Finished All| S["Upsert Remaining Points"]
    S --> T["End / Log Total Count"]
```

---

## 2. Agent & Backend Request Pipeline

TailorTalk operates a production-grade **FastAPI** backend with asynchronous request handling, request-scoped context variables, a thread-safe in-memory session store, and a **LangGraph ReAct agent** powered by Groq (`llama-3.3-70b-versatile`).

**Key Steps:**
1. **API Endpoint (`POST /api/chat`):** Receives `multipart/form-data` containing `session_id`, `message`, and optional `image` file or `image_url`.
2. **Session Store & Context Isolation:**
   - Retrieves or initializes session state in `backend/session_store.py` (lazy agent instantiation, conversation history, cached query vectors, TTL eviction).
   - Injects cached session vectors and empty result containers into request-local context variables (`CURRENT_SESSION_VECTORS`, `LAST_TOOL_RESULTS`).
3. **Async Agent Execution:** Offloads synchronous LangGraph agent execution to a thread-pool executor (`_run_agent_async`) so the FastAPI event loop remains non-blocking.
4. **Agent Reasoning & Tool Invocation:**
   - Groq LLM evaluates conversation history and user input.
   - For general queries, it generates a conversational reply without calling tools.
   - For visual search queries, it calls the `search_similar_sarees` tool:
     - **New Image Query:** Downloads URL or reads uploaded file, extracts 3 feature signals (Full Gemini embedding, HSV Color Histogram, and Border/Pallu crop Gemini embedding with `RETRIEVAL_QUERY`), and executes a 3-signal prefetch search in Qdrant with Reciprocal Rank Fusion (RRF).
     - **Follow-up Filter Query (e.g., "under ₹3000"):** Re-uses cached vectors from `CURRENT_SESSION_VECTORS` without re-embedding, applying Qdrant `FieldCondition` range filters on `discounted_price`.
5. **State Persistence & Response Formatting:**
   - Harvests tool results and updated vectors from `contextvars`.
   - Persists updated vectors and appended chat messages into `session_store`.
   - Returns structured `ChatResponse` containing the text `reply` and an array of `SareeResult` objects.

```mermaid
flowchart TD
    A["Client Request<br/>POST /api/chat"] --> B["FastAPI Router<br/>backend/routers/chat.py"]
    B --> C["Retrieve/Create Session<br/>backend/session_store.py"]
    
    C --> D["Set Request ContextVars<br/>- CURRENT_SESSION_VECTORS<br/>- LAST_TOOL_RESULTS"]
    D --> E["Offload to Threadpool<br/>_run_agent_async"]
    
    E --> F["LangGraph ReAct Agent<br/>src/agent.py"]
    F --> G{"LLM Reasoning<br/>Groq LLaMA-3.3"}
    
    G -->|General Chit-Chat| H["Generate Conversational Response"]
    
    G -->|Search Needed| I["Call Tool: search_similar_sarees"]
    I --> J{"Query Type"}
    
    J -->|Follow-up Price Filter| K["Read Cached Vectors from ContextVar"]
    J -->|New Image Upload / URL| L["Compute 3 Feature Signals<br/>1. Full Gemini Vector (RETRIEVAL_QUERY)<br/>2. HSV Color Histogram (96-dim)<br/>3. Border Crop Gemini Vector (bottom 30%)"]
    
    K --> M["Qdrant Multi-Vector Query<br/>Prefetch + RRF Fusion + Price Filter"]
    L --> M
    
    M --> N["Normalize RRF Scores to Match %<br/>_rrf_to_pct"]
    N --> O["Write Results to LAST_TOOL_RESULTS<br/>Update CURRENT_SESSION_VECTORS"]
    O --> P["Return Matches to Agent"]
    
    P --> G
    H --> Q["Agent Produces Final Reply Text"]
    
    Q --> R["Router Harvests:<br/>- Text Reply<br/>- SareeResult list from LAST_TOOL_RESULTS"]
    R --> S["Persist Vectors & History to session_store"]
    S --> T["Return JSON ChatResponse"]
```

---

## 3. End-to-End User Flow (React + FastAPI)

This flow illustrates the user journey from uploading a saree photo in the React SPA to viewing conversational advice and interactive product cards.

**Key Steps:**
1. **User Interaction (Frontend):** The user accesses the React 18 SPA (`frontend/`), opens the Image Studio sidebar, drops a saree image (or pastes a URL), and types a request (e.g., *"Find me something like this under ₹5,000"*).
2. **HTTP Request:** The `useChat` hook sends a `multipart/form-data` POST request to `/api/chat` containing the `session_id`, text prompt, and image file.
3. **Backend Processing:**
   - FastAPI saves the image to a temporary file, adds context guidance to the prompt, and passes it to the ReAct agent.
   - The agent invokes `search_similar_sarees`, which performs multi-vector extraction and executes 3-signal RRF retrieval against Qdrant.
   - The agent summarizes the matches in natural language, while raw product records are packaged into the JSON payload.
4. **Interactive UI Rendering:**
   - React updates the chat transcript with the assistant's message bubble (rendered with markdown).
   - Below the message, React renders a responsive `ProductGrid` containing `ProductCard` components featuring product imagery, title, match percentage badge, price comparison with retail strikethrough, and a direct link to the boutique store.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant React_UI as React SPA (Frontend)
    participant FastAPI as FastAPI (/api/chat)
    participant SessionStore as Session Store
    participant Agent as LangGraph ReAct Agent
    participant Tool as search_similar_sarees
    participant Embed as Embeddings (Gemini + OpenCV)
    participant Qdrant as Qdrant Vector DB

    User->>React_UI: Uploads Saree Image & Types "Find similar under ₹5,000"
    React_UI->>FastAPI: POST /api/chat (multipart/form-data: session_id, message, file)
    
    FastAPI->>SessionStore: get_or_create(session_id)
    SessionStore-->>FastAPI: Session (agent, history, cached vectors)
    
    FastAPI->>FastAPI: Save upload to temp file & set ContextVars
    FastAPI->>Agent: _run_agent_async(agent, prompt_with_image, history)
    
    Agent->>Agent: LLM analyzes intent & identifies search with price filter
    Agent->>Tool: search_similar_sarees(image_path, max_price=5000)
    
    Tool->>Embed: embed_image_gemini(path, task_type="RETRIEVAL_QUERY")
    Tool->>Embed: compute_color_histogram(path)
    Tool->>Embed: crop_border(path) -> embed_image_gemini(crop_path, task_type="RETRIEVAL_QUERY")
    Embed-->>Tool: 3 Query Vectors (Gemini Full, Color, Gemini Border)
    
    Tool->>Qdrant: query_points(3x Prefetch + FusionQuery(RRF) + Price Filter)
    Qdrant-->>Tool: Top Candidates with RRF scores
    
    Tool->>Tool: Convert RRF scores to Match % (_rrf_to_pct)
    Tool->>FastAPI: Save to LAST_TOOL_RESULTS & update session vectors
    Tool-->>Agent: Return structured product list
    
    Agent->>Agent: LLM summarizes findings into conversational reply
    Agent-->>FastAPI: Text Reply
    
    FastAPI->>SessionStore: update_vectors() + append chat_history
    FastAPI->>FastAPI: Cleanup temporary upload file
    FastAPI-->>React_UI: 200 OK: ChatResponse(reply, results=[SareeResult...])
    
    React_UI->>React_UI: Render Assistant Message Bubble
    React_UI->>React_UI: Render ProductGrid & ProductCard items
    React_UI-->>User: Views Conversational Summary + Saree Cards with Match % & Prices
```

---

