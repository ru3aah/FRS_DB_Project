FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --upgrade pip && pip install uv

# Copy dependency files first (better layer cache)
COPY pyproject.toml uv.lock ./

# Install deps (creates /app/.venv)
RUN uv sync --frozen

# Use venv binaries by default
ENV PATH="/app/.venv/bin:$PATH"

# Copy the rest of the project
COPY . .

# Entrypoint
COPY Docker/django/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]