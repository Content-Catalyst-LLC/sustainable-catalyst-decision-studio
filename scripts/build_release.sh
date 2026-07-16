#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="1.16.0"
OUT="${1:-$ROOT/dist}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PLUGIN_DIR="$ROOT/wordpress-plugin/sustainable-catalyst-decision-studio"
mkdir -p "$OUT"
rm -f "$OUT/sustainable-catalyst-decision-studio-plugin-v${VERSION}.zip" "$OUT/sustainable-catalyst-decision-studio-v${VERSION}-repository.zip"
(
  cd "$ROOT/backend"
  "$PYTHON_BIN" -m compileall -q app tests
  "$PYTHON_BIN" -m pytest
)
"$PYTHON_BIN" "$ROOT/scripts/test_release.py"
php -l "$PLUGIN_DIR/sustainable-catalyst-decision-studio.php"
if command -v node >/dev/null 2>&1; then node --check "$PLUGIN_DIR/assets/js/scds-decision-studio.js"; node --check "$PLUGIN_DIR/assets/js/scds-offline-workspace.js"; fi
find "$ROOT" -type d \( -name '__pycache__' -o -name '.pytest_cache' \) -prune -exec rm -rf {} +
find "$ROOT" -type f -name '*.pyc' -delete
(
  cd "$ROOT/wordpress-plugin"
  zip -qr "$OUT/sustainable-catalyst-decision-studio-plugin-v${VERSION}.zip" sustainable-catalyst-decision-studio -x '*/__pycache__/*' '*.pyc' '*/.DS_Store'
)
(
  cd "$ROOT/.."
  zip -qr "$OUT/sustainable-catalyst-decision-studio-v${VERSION}-repository.zip" "$(basename "$ROOT")" -x '*/__pycache__/*' '*.pyc' '*/.pytest_cache/*' '*/dist/*' '*/.DS_Store'
)
printf 'Built:\n%s\n%s\n' "$OUT/sustainable-catalyst-decision-studio-plugin-v${VERSION}.zip" "$OUT/sustainable-catalyst-decision-studio-v${VERSION}-repository.zip"
