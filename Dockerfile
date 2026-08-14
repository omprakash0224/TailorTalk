# ── Stage 1: Python builder ──────────────────────────────────────────────────
FROM python:3.11-slim AS py-builder

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
#   curl         – used by health-check probes
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from py-builder
COPY --from=py-builder /install/deps /usr/local

WORKDIR /app

# Copy application source
COPY . .

# ── Environment defaults ────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Document port exposed by container
EXPOSE 8000

# ── Healthcheck (Docker-level) ───────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# ── Entrypoint ───────────────────────────────────────────────────────────────
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
