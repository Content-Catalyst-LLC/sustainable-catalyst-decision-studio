#!/usr/bin/env bash
set -Eeuo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-$HOME/Downloads/sustainable-catalyst-decision-studio}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
OUT="${SCDS_DIST_OUT:-$HOME/Downloads}"
VENV="$(mktemp -d /tmp/scds-v320-venv.XXXXXX)"
trap 'rm -rf "$VENV"' EXIT

echo "=== DECISION STUDIO v3.2.0 APPLY ==="
[ -d "$TARGET/.git" ] || { echo "ERROR: target Git repository not found: $TARGET" >&2; exit 1; }
command -v "$PYTHON_BIN" >/dev/null 2>&1 || { echo "ERROR: $PYTHON_BIN is required" >&2; exit 1; }
cd "$TARGET"
# Ignore only the disposable local backend venv; block all other source changes.
if [ -n "$(git status --porcelain --untracked-files=all | grep -v '^?? backend/.venv/' || true)" ]; then
  git status --short
  echo "ERROR: target working tree has source changes" >&2
  exit 1
fi
rm -rf backend/.venv
rsync -a --delete --exclude='.git/' --exclude='dist/' --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='*.pyc' --exclude='.venv/' "$SRC/" "$TARGET/"

echo "=== PYTHON 3.12 VALIDATION ENVIRONMENT ==="
"$PYTHON_BIN" -m venv "$VENV/venv"
source "$VENV/venv/bin/activate"
python -m pip install -q --upgrade pip
python -m pip install -q -r backend/requirements.txt
python --version
python -m pytest --version

echo "=== FULL BACKEND VALIDATION ==="
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
  git commit -m "Decision Studio v3.2.0 — Decision Kernel & Module Contract Foundation"
else
  echo "No new source changes to commit."
fi
git tag -d v3.2.0 >/dev/null 2>&1 || true
git tag -a v3.2.0 -m "Decision Studio v3.2.0 — Decision Kernel & Module Contract Foundation"
git push origin main
git push origin :refs/tags/v3.2.0 >/dev/null 2>&1 || true
git push origin v3.2.0

echo "=== BUILD RELEASE DISTRIBUTABLES ==="
mkdir -p "$OUT"
PYTHON_BIN="$VENV/venv/bin/python" bash scripts/build_release.sh "$OUT"
cp deploy/contabo/upgrade_decision_studio_backend_v3_2_0_contabo.sh "$OUT/"
cp deploy/contabo/deploy_decision_studio_v3_2_0_from_macos.sh "$OUT/"
cp V320_DECISION_KERNEL_MODULE_CONTRACT_FOUNDATION_COMMANDS.txt "$OUT/"
chmod +x "$OUT/upgrade_decision_studio_backend_v3_2_0_contabo.sh" "$OUT/deploy_decision_studio_v3_2_0_from_macos.sh"

echo "=== FINAL SOURCE STATE ==="
git status --short
git log -1 --oneline
git tag --points-at HEAD

echo "PASS - Decision Studio v3.2.0 applied, validated, pushed, tagged, and packaged"
echo "NEXT: cd $OUT && ./deploy_decision_studio_v3_2_0_from_macos.sh"
