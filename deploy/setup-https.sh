#!/usr/bin/env bash
# Switch MCE CRM to https://crm.usemce.com (+ https://quotes.usemce.com).
# Run on the server AFTER the DNS A records exist:
#   crm.usemce.com    A  62.238.116.55
#   quotes.usemce.com A  62.238.116.55
set -euo pipefail
cd /opt/mce-crm/deploy

echo "[1/5] checking DNS..."
for h in crm.usemce.com quotes.usemce.com; do
  ip=$(getent hosts "$h" | awk '{print $1}' | head -1 || true)
  if [ "$ip" != "62.238.116.55" ]; then
    echo "  $h resolves to '${ip:-nothing}' — expected 62.238.116.55."
    echo "  Wait for DNS to propagate (up to 30 min) and run this again."
    exit 1
  fi
  echo "  $h -> $ip OK"
done

echo "[2/5] updating SERVER_URL and renderer origin..."
sed -i 's|^SERVER_URL=.*|SERVER_URL=https://crm.usemce.com|' .env
sed -i 's|http://62.238.116.55:3000|https://crm.usemce.com|g' docker-compose.renderer.yml
grep -H SERVER_URL .env

echo "[3/5] starting Caddy and restarting the stack..."
docker compose -f docker-compose.yml -f docker-compose.renderer.yml -f docker-compose.caddy.yml up -d
docker compose -f docker-compose.yml -f docker-compose.renderer.yml -f docker-compose.caddy.yml restart server worker quote-renderer

echo "[4/5] closing the old direct ports (traffic now goes through HTTPS)..."
ufw delete allow 3000/tcp >/dev/null 2>&1 || true
ufw delete allow 8090/tcp >/dev/null 2>&1 || true
ufw status | grep -E "80|443" || true

echo "[5/5] waiting for the certificate and checking..."
sleep 5
for i in 1 2 3 4 5 6 7 8 9 10; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://crm.usemce.com/healthz || true)
  [ "$code" = "200" ] && break
  echo "  not ready yet (attempt $i)..."; sleep 10
done
echo "CRM:    https://crm.usemce.com    -> HTTP $code"
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 -u "mce:$(grep -i '^password' credentials.local | cut -d: -f2- | tr -d ' ')" https://quotes.usemce.com/ || true)
echo "Quotes: https://quotes.usemce.com -> HTTP $code (login: mce / your CRM password)"
echo "Done. Log in at https://crm.usemce.com"
