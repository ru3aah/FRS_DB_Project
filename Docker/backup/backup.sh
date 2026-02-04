#!/bin/bash
set -e

BACKUP_DIR=/backups
DATE=$(date +"%Y-%m-%d_%H-%M")
FILE="$BACKUP_DIR/frs_db_$DATE.sql.gz"

export PGPASSWORD=$POSTGRES_PASSWORD

pg_dump -h db -U $POSTGRES_USER $POSTGRES_DB | gzip > "$FILE"

# хранить 14 дней
find $BACKUP_DIR -type f -mtime +14 -delete

echo "Backup created: $FILE"

# если контейнер запущен постоянно — спим сутки
sleep 86400