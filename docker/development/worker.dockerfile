# Development Worker Container
FROM python:3.12-slim

WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry package manager
ENV POETRY_VERSION=1.8.2
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Copy package configurations
COPY backend/pyproject.toml backend/poetry.lock* /workspace/

# Configure Poetry to install directly in system environment
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy backend files
COPY backend/ /workspace/

CMD ["celery", "-A", "app.workflows.worker", "worker", "--loglevel=info"]
