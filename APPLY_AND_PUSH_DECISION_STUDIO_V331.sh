#!/usr/bin/env bash
set -Eeuo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-$HOME/Downloads/sustainable-catalyst-decision-studio}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
OUT="${SCDS_DIST_OUT:-$HOME/Downloads}"
VENV="$(mktemp -d /tmp/scds-v331-venv.XXXXXX)"
trap 'rm -rf "$VENV"' EXIT

echo "=== DECISION STUDIO v3.3.1 APPLY — POSTGRESQL MIGRATION REVISION REPAIR ==="
[ -d "$TARGET/.git" ] || { echo "ERROR: target Git repository not found: $TARGET" >&2; exit 1; }
command -v "$PYTHON_BIN" >/dev/null 2>&1 || { echo "ERROR: $PYTHON_BIN is required" >&2; exit 1; }
cd "$TARGET"
DIRTY="$(git status --porcelain --untracked-files=all | grep -Ev '^\?\? (backend/)?\.venv([^/]*)?/' || true)"
if [ -n "$DIRTY" ]; then
  git status --short
  echo "ERROR: target working tree has source changes" >&2
  exit 1
fi
rm -rf backend/.venv backend/.venv-* .venv .venv-*
# v3.3.0 must already be present; do not rewrite that historical tag.
grep -q 'APP_VERSION = "3.3.0"' backend/app/services/decision_service.py || {
  echo "ERROR: expected v3.3.0 source as repair baseline" >&2
  exit 1
}
rsync -a --delete \
  --exclude='.git/' \
  --exclude='dist/' \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  --exclude='*.pyc' \
  --exclude='.venv/' \
  --exclude='.venv-*/' \
  --exclude='*.venv/' \
  --include='.env.persistence-v330.example' \
  --exclude='.env' \
  --exclude='.env.*' \
  "$SRC/" "$TARGET/"

echo "=== PYTHON 3.12 VALIDATION ENVIRONMENT ==="
"$PYTHON_BIN" -m venv "$VENV/venv"
source "$VENV/venv/bin/activate"
python -m pip install -q --upgrade pip
python -m pip install -q -r backend/requirements.txt
python --version
python -m pytest --version

echo "=== FULL BACKEND + MIGRATION REPAIR VALIDATION ==="
cd backend
PYTHONPATH=. python -m pytest -q
cd ..
python scripts/test_release.py
php -l wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php

echo "=== GIT COMMIT / PUSH / TAG ==="
find . -type d \( -name '__pycache__' -o -name '.pytest_cache' \) -prune -exec rm -rf {} +
find . -type f -name '*.pyc' -delete
git add -A
if ! git diff --cached --quiet; then
  git commit -m "Decision Studio v3.3.1 — PostgreSQL Migration Revision Repair"
else
  echo "No new source changes to commit."
fi
git tag -d v3.3.1 >/dev/null 2>&1 || true
git tag -a v3.3.1 -m "Decision Studio v3.3.1 — PostgreSQL Migration Revision Repair"
git push origin main
git push origin :refs/tags/v3.3.1 >/dev/null 2>&1 || true
git push origin v3.3.1

echo "=== BUILD RELEASE DISTRIBUTABLES ==="
mkdir -p "$OUT"
PYTHON_BIN="$VENV/venv/bin/python" bash scripts/build_release.sh "$OUT"
cp deploy/contabo/upgrade_decision_studio_backend_v3_3_1_contabo.sh "$OUT/"
cp deploy/contabo/deploy_decision_studio_v3_3_1_from_macos.sh "$OUT/"
cp V331_POSTGRESQL_MIGRATION_REVISION_REPAIR_COMMANDS.txt "$OUT/"
chmod +x "$OUT/upgrade_decision_studio_backend_v3_3_1_contabo.sh" "$OUT/deploy_decision_studio_v3_3_1_from_macos.sh"

echo "=== FINAL SOURCE STATE ==="
git status --short
git log -1 --oneline
git tag --points-at HEAD

echo "PASS - Decision Studio v3.3.1 applied, validated, pushed, tagged, and packaged"
echo "NEXT: cd $OUT && ./deploy_decision_studio_v3_3_1_from_macos.sh"
