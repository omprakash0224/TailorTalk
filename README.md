<div align="center">

# TailorTalk - Visual Saree Search

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Vite](https://img.shields.io/badge/Vite-B73BFE?style=for-the-badge&logo=vite&logoColor=FFD62E)
![Qdrant](https://img.shields.io/badge/Qdrant-1A002A?style=for-the-badge&logo=qdrant&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-F472B6?style=for-the-badge&logo=groq&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

TailorTalk is a conversational visual search platform designed specifically for ethnic fashion (sarees). It combines advanced multi-modal embeddings, deterministic color analysis, and a LangGraph ReAct agent to provide an intuitive, dialogue-driven shopping experience.

</div>

## 🚀 Setup Steps

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend)
- Docker (optional, for deployment)
- API Keys: 
  - `GROQ_API_KEY` (for openai/gpt-oss-120b or llama-3.3-70b-versatile via Groq)
  - `GEMINI_API_KEY` (for Google GenAI embeddings)
  - Qdrant connection details (if using cloud/remote, otherwise local memory/docker)

### 2. Backend Setup
1. Navigate to the root directory and create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your `.env` file from `.env.example` with the necessary API keys.
4. Run the catalog indexing pipeline to populate Qdrant (if setting up for the first time):
   ```bash
   python scripts/build_index.py
   ```
5. Start the FastAPI server:
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```

### 3. Frontend Setup
1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   npm install
   ```
2. Start the Vite development server:
   ```bash
   npm run dev
   ```
The frontend will typically run on `http://localhost:5173`, proxying API requests to the FastAPI backend.

### 4. Docker Deployment (Production)
The project includes a multi-stage `Dockerfile` that builds both the React SPA and the Python backend, serving them together via FastAPI.
```bash
docker build -t tailortalk .
docker run -p 8000:8000 --env-file .env tailortalk
```

---

## 🧠 Model, Vector-DB, and Framework Choices

### Models
- **Conversational LLM (Agent Reasoning):** `openai/gpt-oss-120b or llama-3.3-70b-versatile` via **Groq**. Chosen for ultra-low latency inference, keeping the multi-turn conversational UI highly responsive.
- **Semantic Embeddings:** `models/gemini-embedding-2-preview` via **Google GenAI**. Extracts rich visual features (fabric drape, weave, styling) into 3072-dimensional L2-normalized vectors.
- **Color Embeddings:** Custom **OpenCV HSV Color Histogram** (96-dimensional, L2-normalized) ensuring absolute color fidelity, which deep neural networks sometimes overlook in favor of structural patterns.

### Vector Database
- **Qdrant:** Used for high-performance vector search.
- **Architecture:** A `sarees` collection utilizing named vectors (`gemini`, `color`) and metadata payload filtering.

### Frameworks
- **Backend:** **FastAPI** handles high-concurrency requests asynchronously, serving the API. In production, the React SPA is bundled separately (see Docker/deployment notes).
- **Frontend:** **React 18 + Vite** provides a modern, fast Single Page Application (SPA) with a dedicated Image Studio Sidebar and interactive product grids.
- **Agent Orchestration:** **LangGraph** orchestrates the ReAct agent, enabling tool calling and conversation history management.

---

## 🎯 Search Quality Enhancements

To accurately capture the nuances of saree designs (color, fabric weave, border motifs), TailorTalk uses a **3-Signal Multi-Vector Fusion** strategy:
1. **Full Image Gemini Embedding:** Captures overall drape and semantic structure.
2. **HSV Color Histogram:** Guarantees strict color tone matching (OpenCV).
3. **Targeted Border & Pallu Crop Embedding:** A bottom 30% crop embedded via Gemini to isolate distinctive border and zari work.

These 3 signals are queried via a **Prefetch pipeline** and merged using **Reciprocal Rank Fusion (RRF)** in Qdrant. 
- **Task Type Asymmetry:** Enforces `RETRIEVAL_DOCUMENT` during indexing and `RETRIEVAL_QUERY` during search for optimal vector alignment.
- **Score Normalization:** RRF scores are mapped to intuitive "Match %" metrics for the user interface.
- **Session-Isolated Vector Caching:** Caches query vectors during active sessions, enabling zero-latency conversational follow-ups (like applying price filters) without recomputing embeddings.

---

## ⚖️ Assumptions & Trade-offs

1. **In-Memory Session Store vs. Distributed Cache (Redis):** 
   - *Assumption:* Designed primarily for single-container deployments (e.g., standard Render service).
   - *Trade-off:* We used an in-memory TTL store for simplicity and speed. Scaling horizontally across multiple replicas would require migrating this state to Redis.
2. **Decoupled Results vs. LLM Context Window:**
   - *Decision:* The agent generates conversational summaries, but rich product JSON payloads are returned side-by-side rather than fed entirely into the prompt.
   - *Trade-off:* Prevents LLM hallucinations on prices/links and reduces token usage, but the LLM lacks deep reasoning over every single metadata field.
3. **Multi-Vector Storage Footprint:**
   - *Trade-off:* Storing multiple vectors (`gemini` and `color`) per catalog item increases database footprint compared to standard single-vector search, but heavily justifies itself with massive gains in visual retrieval fidelity.
4. **Unified Single-Origin Container Serving:**
   - *Decision:* FastAPI mounts and serves the static `frontend/dist` React build.
   - *Trade-off:* Drastically simplifies CORS and deployment orchestration for prototyping/MVPs, though large-scale production architectures might prefer serving static assets via a dedicated CDN (e.g., S3/CloudFront).
