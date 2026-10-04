# =============================================================================
# ConversX Backend — Dockerfile
# Multi-stage build: builder installs deps, runtime is lean.
# CPU-only PyTorch to keep image size down (D-001).
# Model weights are NEVER baked in — they live in Docker named volumes.
# Target: linux/amd64 and linux/arm64 (built via QEMU in CI).
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: builder — install Python dependencies
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools (removed in final stage)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching)
COPY requirements.txt .

# Install CPU-only torch separately to avoid pulling CUDA wheels (~2 GB saved)
# Then install the rest of the dependencies
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir \
        torch==2.5.1 \
        --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: runtime — lean production image
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Security: run as non-root user
RUN groupadd --gid 1001 conversx && \
    useradd --uid 1001 --gid conversx --shell /bin/bash --create-home conversx

# Runtime system dependencies only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=conversx:conversx . .

# Pre-create temp audio, model cache, and HuggingFace cache directories with non-root ownership
# so Docker volume initialization preserves non-root write permissions (Gate A, D-002)
RUN mkdir -p /tmp/conversx-audio /models/whisper /home/conversx/.cache/huggingface && \
    chown -R conversx:conversx /tmp/conversx-audio /models /home/conversx

USER conversx

# Health check (used by compose and deploy.sh)
HEALTHCHECK --interval=15s --timeout=5s --retries=5 --start-period=20s \
    CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

EXPOSE 8000

# Default command (overridden per service in compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
