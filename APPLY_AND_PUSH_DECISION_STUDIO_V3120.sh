#!/usr/bin/env bash
set -Eeuo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-$HOME/Downloads/sustainable-catalyst-decision-studio}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
OUT="${SCDS_DIST_OUT:-$HOME/Downloads}"
VENV="$(mktemp -d /tmp/scds-v3120-venv.XXXXXX)"
trap 'rm -rf "$VENV"' EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }

echo "=== DECISION STUDIO v3.12.0 APPLY — MODULE INTEROPERABILITY & SHARED EVIDENCE ==="
[[ -d "$TARGET/.git" ]] || fail "target Git repository not found: $TARGET"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || fail "$PYTHON_BIN is required"
cd "$TARGET"
DIRTY="$(git status --porcelain --untracked-files=all | grep -Ev '^\?\? (backend/)?\.venv([^/]*)?/' || true)"
if [[ -n "$DIRTY" ]]; then git status --short; fail "target working tree has source changes"; fi
rm -rf backend/.venv backend/.venv-* .venv .venv-*
grep -q 'APP_VERSION = "3.11.0"' backend/app/services/decision_service.py || fail "expected v3.11.0 source as v3.12 baseline"

rsync -a --delete \
  --exclude='.git/' --exclude='dist/' --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='*.pyc' \
  --exclude='.venv/' --exclude='.venv-*/' --exclude='*.venv/' \
  --include='.env.persistence-v330.example' --exclude='.env' --exclude='.env.*' \
  "$SRC/" "$TARGET/"

echo "=== PYTHON 3.12 VALIDATION ENVIRONMENT ==="
"$PYTHON_BIN" -m venv "$VENV/venv"
source "$VENV/venv/bin/activate"
python -m pip install -q --upgrade pip
python -m pip install -q -r backend/requirements.txt
python --version
python -m pytest --version

echo "=== FULL BACKEND + INTEROPERABILITY/SHARED EVIDENCE VALIDATION ==="
cd backend
PYTHONPATH=. python -m pytest -q
cd ..
python scripts/test_release.py
php -l wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php
if command -v node >/dev/null 2>&1; then
  node --check wordpress-plugin/sustainable-catalyst-decision-studio/assets/js/scds-decision-studio.js
  node --check wordpress-plugin/sustainable-catalyst-decision-studio/assets/js/scds-offline-workspace.js
fi
bash -n deploy/contabo/deploy_decision_studio_v3_12_0_from_macos.sh
bash -n deploy/contabo/upgrade_decision_studio_backend_v3_12_0_contabo.sh

echo "=== GIT COMMIT / PUSH / TAG ==="
find . -type d \( -name '__pycache__' -o -name '.pytest_cache' \) -prune -exec rm -rf {} +
find . -type f -name '*.pyc' -delete
git add -A
if ! git diff --cached --quiet; then
  git commit -m "Decision Studio v3.12.0 — Module Interoperability & Shared Evidence"
else
  echo "No new source changes to commit."
fi
git push origin main
if git rev-parse -q --verify refs/tags/v3.12.0 >/dev/null; then
  [[ "$(git rev-list -n1 v3.12.0)" == "$(git rev-parse HEAD)" ]] || fail "tag v3.12.0 already exists on a different commit"
else
  git tag -a v3.12.0 -m "Decision Studio v3.12.0 — Module Interoperability & Shared Evidence"
fi
git push origin v3.12.0

echo "=== BUILD RELEASE DISTRIBUTABLES ==="
mkdir -p "$OUT"
PYTHON_BIN="$VENV/venv/bin/python" bash scripts/build_release.sh "$OUT"
cp deploy/contabo/upgrade_decision_studio_backend_v3_12_0_contabo.sh "$OUT/"
cp deploy/contabo/deploy_decision_studio_v3_12_0_from_macos.sh "$OUT/"
cp V3120_MODULE_INTEROPERABILITY_SHARED_EVIDENCE_COMMANDS.txt "$OUT/"
chmod +x "$OUT/upgrade_decision_studio_backend_v3_12_0_contabo.sh" "$OUT/deploy_decision_studio_v3_12_0_from_macos.sh"

echo "=== FINAL SOURCE STATE ==="
git status --short
git log -1 --oneline
git tag --points-at HEAD

echo "PASS - Decision Studio v3.12.0 applied, validated, pushed, tagged, and packaged"
echo "NEXT: cd $OUT && ./deploy_decision_studio_v3_12_0_from_macos.sh"
