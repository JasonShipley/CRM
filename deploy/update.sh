#!/usr/bin/env bash
# Update MCE CRM on the server to the latest code and restart the quote builder.
# Run on the server as root:   sudo /opt/mce-crm/deploy/update.sh [branch]
# Default branch is main. Safe to re-run.
#
# Leaves your data alone: .env, credentials.local, the database and the stored
# quotes are never touched — they are not in git and live in docker volumes.
set -euo pipefail

BRANCH="${1:-main}"
ROOT=/opt/mce-crm
SRC=$ROOT/src
APP=$ROOT/deploy
REMOTE=https://github.com/JasonShipley/CRM.git

echo "==> [1/4] Fetching '$BRANCH'"
if [ -d "$SRC/.git" ]; then
  git -C "$SRC" fetch --quiet --all --prune
else
  rm -rf "$SRC"
  git clone --quiet "$REMOTE" "$SRC"
fi
git -C "$SRC" checkout --quiet "$BRANCH"
git -C "$SRC" reset --quiet --hard "origin/$BRANCH"
echo "    now at $(git -C "$SRC" log --oneline -1)"

echo "==> [2/4] Installing app code"
# renderer/ is the whole app. deploy/ only its tracked files — .env and
# credentials.local are gitignored, so they are not in $SRC and survive.
rm -rf "$ROOT/renderer"
cp -r "$SRC/renderer" "$ROOT/"
cp "$SRC/deploy/"*.yml "$SRC/deploy/"*.sh "$SRC/deploy/Caddyfile" "$APP/"
chmod +x "$APP"/*.sh

echo "==> [3/4] Rebuilding the quote builder (a few minutes on first run)"
cd "$APP"
COMPOSE=(-f docker-compose.yml -f docker-compose.renderer.yml)
[ -f docker-compose.caddy.yml ] && COMPOSE+=(-f docker-compose.caddy.yml)
docker compose "${COMPOSE[@]}" up -d --build quote-renderer

echo "==> [4/4] Checking it came up"
pass=$(grep -i '^password' credentials.local | cut -d: -f2- | tr -d ' ')
for i in $(seq 1 12); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
    -u "mce:$pass" https://quotes.usemce.com/ || true)
  [ "$code" = "200" ] && break
  echo "    not ready yet (attempt $i, HTTP ${code:-none})..."; sleep 10
done
echo
echo "Quote builder: https://quotes.usemce.com  -> HTTP $code"
echo "Calculators:   https://quotes.usemce.com/tools"
echo "Login:         mce / (the CRM password in deploy/credentials.local)"
[ "$code" = "200" ] || {
  echo
  echo "Not answering yet. Check:  docker compose ${COMPOSE[*]} logs --tail 50 quote-renderer"
  exit 1
}
