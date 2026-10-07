#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="3.7.0"
OUT="${1:-$ROOT/dist}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PLUGIN_DIR="$ROOT/wordpress-plugin/sustainable-catalyst-decision-studio"
mkdir -p "$OUT"
rm -f "$OUT/sustainable-catalyst-decision-studio-plugin-v${VERSION}.zip" "$OUT/sustainable-catalyst-decision-studio-v${VERSION}-repository.zip" "$OUT/sustainable-catalyst-decision-studio-backend-v${VERSION}.zip"
(
  cd "$ROOT/backend"
  "$PYTHON_BIN" -m compileall -q app tests migrations
  PYTHONPATH=. "$PYTHON_BIN" -m pytest -q
)
"$PYTHON_BIN" "$ROOT/scripts/test_release.py"
php -l "$PLUGIN_DIR/sustainable-catalyst-decision-studio.php"
if command -v node >/dev/null 2>&1; then node --check "$PLUGIN_DIR/assets/js/scds-decision-studio.js"; node --check "$PLUGIN_DIR/assets/js/scds-offline-workspace.js"; fi
find "$ROOT" -type d \( -name '__pycache__' -o -name '.pytest_cache' \) -prune -exec rm -rf {} +
find "$ROOT" -type f -name '*.pyc' -delete
(
  cd "$ROOT/wordpress-plugin"
  zip -qr "$OUT/sustainable-catalyst-decision-studio-plugin-v${VERSION}.zip" sustainable-catalyst-decision-studio -x '*/__pycache__/*' '*.pyc' '*/.DS_Store' '*/.venv*/*'
)
REPO_STAGE="$(mktemp -d "${TMPDIR:-/tmp}/scds-repository-v370.XXXXXX")"
mkdir -p "$REPO_STAGE/sustainable-catalyst-decision-studio"
rsync -a --exclude='.git/' --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='*.pyc' --exclude='dist/' --exclude='.DS_Store' --exclude='.venv/' --exclude='.venv-*/' --exclude='*.venv/' --include='.env.persistence-v330.example' --exclude='.env' --exclude='.env.*' "$ROOT/" "$REPO_STAGE/sustainable-catalyst-decision-studio/"
(cd "$REPO_STAGE" && zip -qr "$OUT/sustainable-catalyst-decision-studio-v${VERSION}-repository.zip" sustainable-catalyst-decision-studio)
rm -rf "$REPO_STAGE"
BACKEND_STAGE="$(mktemp -d "${TMPDIR:-/tmp}/scds-backend-v370.XXXXXX")"
trap 'rm -rf "$BACKEND_STAGE"' EXIT
BASE="$BACKEND_STAGE/sustainable-catalyst-decision-studio-backend-v${VERSION}"
mkdir -p "$BASE/backend"
rsync -a --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='*.pyc' --exclude='.env' --exclude='.env.*' --exclude='.venv/' --exclude='.venv-*/' "$ROOT/backend/" "$BASE/backend/"
cp "$ROOT/compose.yml" "$BASE/compose.v3.7.0.yml"
cp "$ROOT/.env.persistence-v330.example" "$BASE/.env.persistence-v330.example"
(cd "$BACKEND_STAGE" && zip -qr "$OUT/sustainable-catalyst-decision-studio-backend-v${VERSION}.zip" "sustainable-catalyst-decision-studio-backend-v${VERSION}")
rm -rf "$BACKEND_STAGE"
trap - EXIT
printf 'Built:\n%s\n%s\n%s\n' "$OUT/sustainable-catalyst-decision-studio-plugin-v${VERSION}.zip" "$OUT/sustainable-catalyst-decision-studio-v${VERSION}-repository.zip" "$OUT/sustainable-catalyst-decision-studio-backend-v${VERSION}.zip"
