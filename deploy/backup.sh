#!/usr/bin/env bash
# Nightly backup of the Twenty CRM database + uploaded files.
# Install (as root on the server):  crontab -e  ->  add:
#   15 2 * * * /opt/mce-crm/deploy/backup.sh >> /var/log/mce-crm-backup.log 2>&1
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/mce-crm}"
KEEP_DAYS="${KEEP_DAYS:-30}"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR"

# 1) database dump (compressed)
docker compose -f "$DEPLOY_DIR/docker-compose.yml" exec -T db \
  pg_dump -U postgres -d default | gzip > "$BACKUP_DIR/twenty-db-$STAMP.sql.gz"

# 2) uploaded files volume (attachments, workspace logos)
docker run --rm -v twenty_server-local-data:/data -v "$BACKUP_DIR":/backup alpine \
  tar czf "/backup/twenty-files-$STAMP.tar.gz" -C /data .

# 3) prune old backups
find "$BACKUP_DIR" -name 'twenty-*' -mtime +"$KEEP_DAYS" -delete

echo "$(date -Is) backup complete: $BACKUP_DIR/twenty-db-$STAMP.sql.gz"
