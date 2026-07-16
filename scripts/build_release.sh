#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="1.7.1"
OUT="${1:-$ROOT/dist}"
PLUGIN_DIR="$ROOT/wordpress-plugin/sustainable-catalyst-decision-studio"
mkdir -p "$OUT"
rm -f "$OUT/sustainable-catalyst-decision-studio-plugin-v${VERSION}.zip" "$OUT/sustainable-catalyst-decision-studio-v${VERSION}-repository.zip"
(
  cd "$ROOT/backend"
  python -m compileall -q app tests
  python -m pytest
)
python "$ROOT/scripts/test_release.py"
php -l "$PLUGIN_DIR/sustainable-catalyst-decision-studio.php"
(
  cd "$ROOT/wordpress-plugin"
  zip -qr "$OUT/sustainable-catalyst-decision-studio-plugin-v${VERSION}.zip" sustainable-catalyst-decision-studio -x '*/__pycache__/*' '*.pyc'
)
(
  cd "$ROOT/.."
  zip -qr "$OUT/sustainable-catalyst-decision-studio-v${VERSION}-repository.zip" "$(basename "$ROOT")" -x '*/__pycache__/*' '*.pyc' '*/.pytest_cache/*' '*/dist/*'
)
printf 'Built:\n%s\n%s\n' "$OUT/sustainable-catalyst-decision-studio-plugin-v${VERSION}.zip" "$OUT/sustainable-catalyst-decision-studio-v${VERSION}-repository.zip"
