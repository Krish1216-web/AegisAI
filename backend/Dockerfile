# ==============================================================================
# AegisAI Enterprise — Production Backend Dockerfile (Context: backend/)
# ==============================================================================

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

COPY pyproject.toml poetry.lock* /build/

RUN poetry config virtualenvs.create false \
    && poetry export --without-hashes --without dev -f requirements.txt -o requirements.txt

RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt


FROM python:3.12-slim AS runtime

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/wheels /wheels
COPY --from=builder /build/requirements.txt .
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels requirements.txt

RUN groupadd -g 10001 aegisgroup && \
    useradd -u 10001 -g aegisgroup -m -s /bin/bash aegisuser

RUN mkdir -p /workspace/storage /workspace/logs && \
    chown -R aegisuser:aegisgroup /workspace

COPY --chown=aegisuser:aegisgroup . /workspace/

ENV PYTHONPATH="/workspace" \
    PYTHONUNBUFFERED="1" \
    PYTHONDONTWRITEBYTECODE="1" \
    ENVIRONMENT="prod" \
    DOCUMENT_STORAGE_PATH="/workspace/storage"

USER aegisuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
