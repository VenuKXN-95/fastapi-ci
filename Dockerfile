# ==============================================================================
# Production Dockerfile — FastAPI Service
# Multi-stage build: builder → runtime
# Built with BuildKit (DOCKER_BUILDKIT=1)
# ==============================================================================

# ---------------------------------------------------------------------------
# Stage 1: builder
# Installs dependencies into a clean virtual environment.
# This stage is never shipped; only the venv is copied.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Reproducible build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION="1.0.0"

WORKDIR /build

# System build deps (compile wheels that have C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create isolated virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip inside the venv (pinned pip for reproducibility)
RUN pip install --upgrade pip==24.3.1

# Copy dependency manifests first (Docker layer caching)
COPY requirements.txt ./

# Install runtime dependencies only (no dev tools in image)
RUN pip install --no-cache-dir --require-hashes --requirement requirements.txt || \
    pip install --no-cache-dir --requirement requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: runtime
# Minimal, non-root production image.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# OCI Image labels
LABEL org.opencontainers.image.title="FastAPI CI Service" \
      org.opencontainers.image.description="Production-grade FastAPI service" \
      org.opencontainers.image.source="https://github.com/VenuKXN-95/fastapi-ci" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.licenses="MIT"

# Runtime system dependencies only
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
      libpq5 \
      curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create a non-root user and group (least privilege)
RUN groupadd --system --gid 1001 appgroup && \
    useradd  --system --uid 1001 --gid appgroup --no-create-home appuser

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source (only what is needed at runtime)
COPY app/ ./app/

# Fix ownership
RUN chown -R appuser:appgroup /app

# Drop to non-root
USER appuser

# Expose the application port
EXPOSE 8000

# Health check — used by Docker, K8s, and ECS
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl --fail --silent http://localhost:8000/api/v1/health || exit 1

# Default entrypoint using Uvicorn
# Override WORKERS with environment variable for horizontal scaling
ENV WORKERS=1 \
    HOST=0.0.0.0 \
    PORT=8000

CMD ["sh", "-c", \
     "uvicorn app.main:app \
        --host ${HOST} \
        --port ${PORT} \
        --workers ${WORKERS} \
        --access-log \
        --log-level info"]
