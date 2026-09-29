#!/usr/bin/env bash
# Update MCE CRM on the server to the latest code and restart the quote builder.
# Run on the server as root:   sudo /opt/mce-crm/deploy/update.sh [branch]
# With no branch it deploys the repository's default branch, whatever that is
# named — this repo has no "main". Safe to re-run.
#
# Leaves your data alone: .env, credentials.local, the database and the stored
# quotes are never touched — they are not in git and live in docker volumes.
set -euo pipefail

BRANCH="${1:-}"
ROOT=/opt/mce-crm
SRC=$ROOT/src
APP=$ROOT/deploy
REMOTE=https://github.com/JasonShipley/CRM.git

echo "==> [1/4] Fetching"
if [ -d "$SRC/.git" ]; then
  git -C "$SRC" fetch --quiet --all --prune
else
  rm -rf "$SRC"
  git clone --quiet "$REMOTE" "$SRC"
fi

if [ -z "$BRANCH" ]; then
  # Ask the remote which branch is its default rather than assuming "main".
  BRANCH=$(git -C "$SRC" remote show origin | sed -n 's/.*HEAD branch: //p')
  [ -n "$BRANCH" ] || { echo "Could not determine the default branch. Pass one:"; \
                        echo "  $0 <branch>"; exit 1; }
  echo "    default branch is '$BRANCH'"
fi
git -C "$SRC" show-ref --verify --quiet "refs/remotes/origin/$BRANCH" || {
  echo "    branch '$BRANCH' does not exist on the remote. Available:"
  git -C "$SRC" for-each-ref --format='      %(refname:short)' refs/remotes/origin | grep -v HEAD
  exit 1
}
git -C "$SRC" checkout --quiet -B "$BRANCH" "origin/$BRANCH"
git -C "$SRC" reset --quiet --hard "origin/$BRANCH"
echo "    deploying '$BRANCH' at $(git -C "$SRC" log --oneline -1)"

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

echo "==> [4/5] Reloading the proxy"
# Caddy mounts deploy/Caddyfile read-only and does not notice it changing, so a
# routing change (for instance /api/ bypassing basic auth so bearer tokens
# survive) would sit on disk unapplied. `caddy reload` is graceful — it does not
# drop TLS or in-flight requests.
if docker compose "${COMPOSE[@]}" ps --status running --services 2>/dev/null | grep -qx caddy; then
  if docker compose "${COMPOSE[@]}" exec -T caddy \
       caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile; then
    echo "    Caddyfile reloaded"
  else
    echo "    reload failed — restarting Caddy instead"
    docker compose "${COMPOSE[@]}" up -d --force-recreate caddy
  fi
else
  echo "    Caddy is not running here; skipping"
fi

echo "==> [5/5] Checking it came up"
pass=$(grep -i '^password' credentials.local | cut -d: -f2- | tr -d ' ')
for i in $(seq 1 12); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
    -u "mce:$pass" https://quotes.usemce.com/ || true)
  [ "$code" = "200" ] && break
  echo "    not ready yet (attempt $i, HTTP ${code:-none})..."; sleep 10
done
# The API is routed past basic auth so bearer tokens survive, which makes the app
# the only guard in front of it. Unauthenticated it MUST answer 401 — a 200 here
# means MCE's pricing basis and every quote are readable from the internet.
api=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
  https://quotes.usemce.com/api/pricing || true)

echo
echo "Quote builder: https://quotes.usemce.com  -> HTTP $code"
echo "Calculators:   https://quotes.usemce.com/tools"
echo "Login:         mce / (the password in deploy/credentials.local)"
echo "API, no token: HTTP $api (401 is correct — it means the API is locked)"
[ "$code" = "200" ] || {
  echo
  echo "Not answering yet. Check:  docker compose ${COMPOSE[*]} logs --tail 50 quote-renderer"
  exit 1
}
[ "$api" = "401" ] || {
  echo
  echo "STOP. /api/pricing answered $api without a token; it must answer 401."
  echo "The API is reachable from the internet. Check the app came up on this"
  echo "build and that deploy/Caddyfile is the one in git."
  exit 1
}
