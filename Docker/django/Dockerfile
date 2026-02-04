FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Копируем весь проект (у тебя uv/pyproject, requirements.txt может не быть)
COPY . .

# Установим зависимости через uv (у тебя есть uv.lock)
RUN pip install --upgrade pip && pip install uv \
    && uv sync --frozen

# collectstatic (если настройка STATIC_ROOT есть — ок)
RUN uv run python manage.py collectstatic --noinput

# ВАЖНО: путь с учётом твоей структуры: Docker/...
COPY Docker/django/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]