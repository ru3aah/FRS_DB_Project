.PHONY: help up down build rebuild restart logs migrate makemigrations shell web db collectstatic

PROJECT=FRS_DB_Project
WEB_CONTAINER=frs_web
DB_CONTAINER=frs_db

help:
	@echo ""
	@echo "Available commands:"
	@echo "  make up               Start all containers"
	@echo "  make down             Stop all containers"
	@echo "  make restart          Restart all containers"
	@echo "  make build            Build web image"
	@echo "  make rebuild          Rebuild web image (no cache)"
	@echo "  make logs             Show web container logs"
	@echo "  make migrate          Run Django migrations"
	@echo "  make makemigrations   Create Django migrations"
	@echo "  make collectstatic    Collect static files"
	@echo "  make shell            Django shell inside web"
	@echo "  make web              Bash inside web container"
	@echo "  make db               PostgreSQL shell"
	@echo ""

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose down
	docker compose up -d

build:
	docker compose build web

rebuild:
	docker compose build --no-cache web

logs:
	docker logs -f $(WEB_CONTAINER) --tail=200

migrate:
	docker compose exec web uv run python manage.py migrate

makemigrations:
	docker compose exec web uv run python manage.py makemigrations

collectstatic:
	docker compose exec web uv run python manage.py collectstatic --noinput

shell:
	docker compose exec web uv run python manage.py shell

web:
	docker compose exec web bash

db:
	docker compose exec db psql -U $$POSTGRES_USER $$POSTGRES_DB