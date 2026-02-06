#!/bin/bash
set -e

echo "🧹 Очистка старых бэкапов..."
rm -f /backups/*.sql.gz

# Имя файла
BACKUP_FILE="frs_db_latest.sql.gz"
BACKUP_DIR="/backups"

# Убедись, что переменные окружения проброшены
echo "📦 Создание нового бэкапа: $BACKUP_FILE"
PGPASSWORD="${PGPASSWORD}" pg_dump -h db -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

echo "✅ Бэкап создан: ${BACKUP_DIR}/${BACKUP_FILE}"