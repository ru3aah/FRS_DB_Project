# ========= FRS_DB_PROJECT Makefile =========

# Подгрузить переменные из .env (для make)
ifneq (,$(wildcard .env))
	include .env
	export
endif

# docker compose v2 по умолчанию; при желании можно переопределить:
# make COMPOSE=docker-compose up
COMPOSE ?= docker compose

# Удобный алиас для Django-команд внутри контейнера web (venv через uv)
DJANGO = $(COMPOSE) exec web uv run python manage.py

.PHONY: up down restart logs build shell migrate createsuperuser collectstatic status prune rebuild restore backup test reset-db dev-cert deploy

# 🔼 Запуск
up:
	@echo "Запуск проекта..."
	$(COMPOSE) up --build -d

# 🔽 Остановка
down:
	@echo "Остановка проекта..."
	$(COMPOSE) down --remove-orphans

# ♻️ Перезапуск
restart:
	@$(MAKE) down
	@$(MAKE) up

# 🏗️ Пересборка
build:
	$(COMPOSE) build --no-cache

# 📋 Логи
logs:
	$(COMPOSE) logs -f --tail=100

# 🐚 Шелл внутри web
shell:
	$(COMPOSE) exec web sh

# 🗃️ Миграции Django
migrate:
	$(DJANGO) migrate

# 👤 Суперпользователь Django
createsuperuser:
	$(DJANGO) createsuperuser

# 🧾 Сборка статики
collectstatic:
	$(DJANGO) collectstatic --noinput

# 📦 Статус контейнеров
status:
	$(COMPOSE) ps

# 🧹 Очистка builder-кэша
prune:
	docker builder prune --all --force

# 🔨 Пересборка всего
rebuild:
	@$(MAKE) down
	@$(MAKE) prune
	@$(MAKE) up

# 💾 Safely create a single up-to-date backup (в контейнере db)
# Важно: pipefail + test -s, чтобы не получались "пустые" gzip при ошибке pg_dump
backup:
	$(COMPOSE) exec -T db sh -c '\
		set -euo pipefail; \
		mkdir -p /backups; \
		echo "Preparing to create a new backup..."; \
		if [ -f /backups/frs_db_latest.sql.gz ]; then \
			mv /backups/frs_db_latest.sql.gz /backups/frs_db_old.sql.gz; \
		fi; \
		echo "Creating new backup..."; \
		PGPASSWORD="$$POSTGRES_PASSWORD" pg_dump -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" | gzip -c > /backups/frs_db_latest.sql.gz; \
		test -s /backups/frs_db_latest.sql.gz; \
		echo "New backup created: /backups/frs_db_latest.sql.gz"; \
		rm -f /backups/frs_db_old.sql.gz; \
		echo "Old backup removed (if it existed)"; \
	'

# ♻️ Restore the database from the latest backup (в контейнере db)
# Делает restore "без танцев": сначала чистит schema public, затем льёт дамп.
# Плюс: ON_ERROR_STOP=1, чтобы psql падал на любой ошибке (а не печатал ERROR и ехал дальше).
restore:
	$(COMPOSE) exec -T db sh -c '\
		set -euo pipefail; \
		if [ ! -f /backups/frs_db_latest.sql.gz ]; then \
			echo "Backup file /backups/frs_db_latest.sql.gz not found!"; \
			exit 1; \
		fi; \
		echo "Dropping public schema..."; \
		PGPASSWORD="$$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"; \
		echo "Restoring from /backups/frs_db_latest.sql.gz..."; \
		PGPASSWORD="$$POSTGRES_PASSWORD" gunzip -c /backups/frs_db_latest.sql.gz | psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"; \
		echo "Database successfully restored."; \
	'

# 🧪 Тесты Django
test:
	$(DJANGO) test

# 💣 Сброс БД (используем переменные окружения из .env/compose)
reset-db:
	@echo "Сброс базы данных..."
	$(COMPOSE) exec -T db psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# 🔐 Генерация dev SSL через mkcert
dev-cert:
	@echo "Создание сертификатов через mkcert..."
	@if ! mkcert -help > /dev/null 2>&1; then \
		echo "mkcert не установлен! Установи: https://github.com/FiloSottile/mkcert"; \
		exit 1; \
	fi
	@mkdir -p certs
	mkcert -cert-file certs/localhost.crt -key-file certs/localhost.key localhost

# 🚀 Псевдодеплой (на сервер с docker)
deploy:
	@echo "Псевдо-деплой на удалённый сервер..."
	@echo "TODO: настроить ssh/scp/docker login для деплоя"
