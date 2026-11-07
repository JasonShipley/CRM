#!/usr/bin/env bash
# Copy the MCE dryer calculator engine from the Engineering repo into the quote renderer.
# The renderer imports this snapshot (PYTHONPATH=/app/vendor), so the container needs no access to
# the Engineering repo. Re-run after any change to the calculator, then rebuild the renderer:
#   renderer/vendor/sync_from_engineering.sh /path/to/Engineering
#   cd deploy && docker compose -f docker-compose.yml -f docker-compose.renderer.yml up -d --build quote-renderer
set -euo pipefail
SRC="${1:?usage: sync_from_engineering.sh /path/to/Engineering}"
HERE="$(cd "$(dirname "$0")" && pwd)"
DST="$HERE/mce_engineering"
rm -rf "$DST"
mkdir -p "$DST/core" "$DST/equipment/dryer_calc/assets"
cp "$SRC/mce_engineering/__init__.py" "$DST/"
cp "$SRC/mce_engineering/core/__init__.py" "$SRC/mce_engineering/core/provenance.py" "$SRC/mce_engineering/core/audit.py" \
   "$DST/core/"
cp "$SRC/mce_engineering/equipment/__init__.py" "$DST/equipment/"
cp "$SRC"/mce_engineering/equipment/dryer_calc/*.py "$DST/equipment/dryer_calc/"
cp "$SRC"/mce_engineering/equipment/dryer_calc/assets/*.png "$SRC"/mce_engineering/equipment/dryer_calc/assets/*.js \
   "$DST/equipment/dryer_calc/assets/"
COMMIT="$(git -C "$SRC" rev-parse --short HEAD 2>/dev/null || echo unknown)"
DIRTY="$(git -C "$SRC" status --porcelain -- mce_engineering 2>/dev/null | head -1)"
printf 'Source: Engineering repo, mce_engineering/equipment/dryer_calc\nCommit: %s%s\nSynced: %s\n' \
  "$COMMIT" "${DIRTY:+ (plus uncommitted changes)}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$HERE/VENDORED.txt"
echo "synced dryer_calc from $SRC @ $COMMIT"
