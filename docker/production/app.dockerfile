# ==============================================================================
# AegisAI Enterprise — Production Backend Dockerfile (Multi-Stage Build)
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build Dependencies
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV POETRY_VERSION=1.8.2
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

COPY backend/pyproject.toml backend/poetry.lock* /build/

# Export runtime dependencies only (excluding dev tools)
RUN poetry config virtualenvs.create false \
    && poetry export --without-hashes --without dev -f requirements.txt -o requirements.txt

# Compile dependency wheels into target cache
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt


# ------------------------------------------------------------------------------
# Stage 2: Production Minimal Runtime
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pre-built wheels from builder stage
COPY --from=builder /build/wheels /wheels
COPY --from=builder /build/requirements.txt .
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels requirements.txt

# Create dedicated non-root runtime system user
RUN groupadd -g 10001 aegisgroup && \
    useradd -u 10001 -g aegisgroup -m -s /bin/bash aegisuser

# Create persistent storage directories with non-root ownership
RUN mkdir -p /workspace/storage /workspace/logs && \
    chown -R aegisuser:aegisgroup /workspace

# Copy backend application source
COPY --chown=aegisuser:aegisgroup backend/ /workspace/

ARG APP_VERSION=1.0.0
ARG GIT_COMMIT_SHA=unknown
ARG BUILD_TIMESTAMP=""

# Set Python environment variables for container runtime
ENV PYTHONPATH="/workspace" \
    PYTHONUNBUFFERED="1" \
    PYTHONDONTWRITEBYTECODE="1" \
    ENVIRONMENT="prod" \
    APP_VERSION="${APP_VERSION}" \
    GIT_COMMIT_SHA="${GIT_COMMIT_SHA}" \
    BUILD_TIMESTAMP="${BUILD_TIMESTAMP}" \
    DOCUMENT_STORAGE_PATH="/workspace/storage"

USER aegisuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production ASGI server with proxy header support for reverse proxy integration
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
