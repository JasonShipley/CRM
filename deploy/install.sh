#!/usr/bin/env bash
# MCE CRM production installer — runs on the Hetzner server as root.
# Idempotent: safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"

echo "==> [1/8] Base packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg ufw cron >/dev/null

echo "==> [2/8] Docker"
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh >/dev/null
fi
systemctl enable --now docker >/dev/null 2>&1 || true

echo "==> [3/8] Firewall (SSH, HTTP, HTTPS, CRM, renderer)"
ufw allow 22/tcp >/dev/null; ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null
ufw allow 3000/tcp >/dev/null; ufw allow 8090/tcp >/dev/null
ufw --force enable >/dev/null

echo "==> [4/8] Install files to /opt/mce-crm"
mkdir -p /opt/mce-crm
cp -r deploy renderer /opt/mce-crm/
chmod 600 /opt/mce-crm/deploy/.env /opt/mce-crm/deploy/credentials.local
chmod +x /opt/mce-crm/deploy/backup.sh
cd /opt/mce-crm/deploy

echo "==> [5/8] Database + files restore"
docker compose up -d db redis
for i in $(seq 1 60); do
  docker compose exec -T db pg_isready -U postgres -h localhost >/dev/null 2>&1 && break
  sleep 2
done
HAS_DATA=$(docker compose exec -T db psql -U postgres -d default -tAc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='core'" 2>/dev/null || echo 0)
if [ "${HAS_DATA:-0}" -gt 0 ]; then
  echo "    database already contains data — skipping restore (delete the 'twenty_db-data' volume to force)"
else
  gunzip -c "$OLDPWD/twenty-db.sql.gz" | docker compose exec -T db psql -q -U postgres -d default
  echo "    database restored"
fi
docker volume inspect twenty_server-local-data >/dev/null 2>&1 || docker volume create twenty_server-local-data >/dev/null
docker run --rm -v twenty_server-local-data:/data -v "$OLDPWD":/backup alpine \
  sh -c "tar xzf /backup/twenty-files.tar.gz -C /data" >/dev/null
echo "    uploaded-files volume restored"

echo "==> [6/8] Start Twenty + quote renderer (renderer image build takes a few minutes)"
docker compose -f docker-compose.yml -f docker-compose.renderer.yml up -d --build

echo "==> [7/8] Nightly backups (2:15 AM, 30-day retention)"
( crontab -l 2>/dev/null | grep -v mce-crm/deploy/backup.sh ; \
  echo "15 2 * * * /opt/mce-crm/deploy/backup.sh >> /var/log/mce-crm-backup.log 2>&1" ) | crontab -

echo "==> [8/8] Rotating root password (the old one was shared during setup)"
NEWPW=$(tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 20)
echo "root:$NEWPW" | chpasswd

echo
echo "=================================================================="
echo "  MCE CRM is up."
echo "  CRM:            http://62.238.116.55:3000"
echo "  Quote renderer: http://62.238.116.55:8090"
echo "  Login: see credentials.local (same as before)"
echo
echo "  NEW root password (save it in your password manager NOW):"
echo "      $NEWPW"
echo "=================================================================="
