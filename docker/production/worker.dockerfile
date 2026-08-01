# Production Stage 1: Build dependencies
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

# Export dependencies
RUN poetry config virtualenvs.create false \
    && poetry export --without-hashes --without dev -f requirements.txt -o requirements.txt

# Compile dependency wheels
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt


# Production Stage 2: Runtime image
FROM python:3.12-slim

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy wheel packages
COPY --from=builder /build/wheels /wheels
COPY --from=builder /build/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copy backend files
COPY backend/ /workspace/

RUN useradd -m aegisuser && chown -R aegisuser:aegisuser /workspace
USER aegisuser

CMD ["celery", "-A", "app.workflows.worker", "worker", "--loglevel=info"]
