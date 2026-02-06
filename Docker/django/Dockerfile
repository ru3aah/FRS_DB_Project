FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including postgresql-client
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    postgresql-client \
 && rm -rf /var/lib/apt/lists/*

# Install uv (Python dependency manager)
RUN pip install --upgrade pip && pip install uv

# Copy and install Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Copy project files
COPY . .

# Copy entrypoint script
COPY Docker/django/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]