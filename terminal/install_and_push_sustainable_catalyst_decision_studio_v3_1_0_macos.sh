#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="3.1.0"
REPO="${1:-$HOME/Downloads/sustainable-catalyst-decision-studio}"
PY="${PYTHON_BIN:-python3}"
fail(){ echo "ERROR: $*" >&2; exit 1; }
[[ -d "$REPO/.git" ]] || fail "Not a Git checkout: $REPO"
cd "$REPO"
[[ "$(git branch --show-current)" == "main" ]] || fail "Expected main branch"

echo "=== DECISION STUDIO v3.1.0 VALIDATION ==="
"$PY" -m compileall -q backend/app backend/tests
(cd backend && PYTHONPATH=. "$PY" -m pytest -q)
"$PY" scripts/test_release.py
php -l wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php
bash -n deploy/contabo/upgrade_decision_studio_backend_v3_1_0_contabo.sh
bash -n deploy/contabo/deploy_decision_studio_v3_1_0_from_macos.sh

echo "=== BUILD DISTRIBUTABLES ==="
rm -rf /tmp/scds-v310-dist
mkdir -p /tmp/scds-v310-dist
PYTHON_BIN="$PY" bash scripts/build_release.sh /tmp/scds-v310-dist
cp /tmp/scds-v310-dist/* "$HOME/Downloads/"
cp deploy/contabo/upgrade_decision_studio_backend_v3_1_0_contabo.sh "$HOME/Downloads/"
cp deploy/contabo/deploy_decision_studio_v3_1_0_from_macos.sh "$HOME/Downloads/"
chmod +x "$HOME/Downloads/"*v3_1_0*.sh 2>/dev/null || true

echo "=== GIT ==="
git status --short
git add -A
git commit -m "Decision Studio v3.1.0 — Backend Service Decomposition"
git tag -a v3.1.0 -m "Decision Studio v3.1.0 — Backend Service Decomposition"
git push origin main
git push origin v3.1.0

echo "PASS: Decision Studio v3.1.0 committed, tagged, pushed, and distributables built."
