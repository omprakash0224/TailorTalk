# ── Stage 1: builder ────────────────────────────────────────────────────────
# Install Python dependencies into a clean prefix so we can copy only what
# we need into the final image (keeps the image as small as possible).
FROM python:3.11-slim AS builder

WORKDIR /install

# System packages needed to compile some wheels (e.g. grpcio)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --prefix=/install/deps --no-cache-dir -r requirements.txt


# ── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Runtime system packages:
#   libgl1       – OpenCV (cv2) requires libGL.so.1
#   libglib2.0-0 – OpenCV dependency (GLib)
#   curl         – used by Render health-check probes (optional but handy)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from the builder stage
COPY --from=builder /install/deps /usr/local

WORKDIR /app

# Copy application source (see .dockerignore for exclusions)
COPY . .

# ── Environment defaults ────────────────────────────────────────────────────
# Render injects PORT at runtime; Streamlit is configured to honour it via
# the STREAMLIT_SERVER_PORT env var (see .streamlit/config.toml as well).
# Never bake real secrets into the image — set them in the Render dashboard.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8501 \
    HEALTH_PORT=8502 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

# Document the ports the container exposes.
# Render only routes external traffic to $PORT (the Streamlit UI).
EXPOSE 8501
EXPOSE 8502

# ── Healthcheck (Docker-level) ───────────────────────────────────────────────
# Streamlit ships a built-in liveness endpoint at /_stcore/health.
# start-period is intentionally generous (60s): loading langchain + google.genai
# + qdrant-client on a fresh Render container takes 20-40s on the first boot.
# Render's own health check (render.yaml: healthCheckPath) uses the same endpoint.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:${PORT:-8501}/_stcore/health || exit 1

# ── Entrypoint ───────────────────────────────────────────────────────────────
# Render injects PORT=10000 at runtime; we pass it explicitly to Streamlit.
# The ${PORT:-8501} fallback keeps the image runnable locally without any env vars.
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]
