#!/usr/bin/env bash
set -Eeuo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-$HOME/Downloads/sustainable-catalyst-decision-studio}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
OUT="${SCDS_DIST_OUT:-$HOME/Downloads}"
VENV="$(mktemp -d /tmp/scds-v3150-venv.XXXXXX)"
trap 'rm -rf "$VENV"' EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }

echo "=== DECISION STUDIO v3.15.0 APPLY — DECISION EVENT STORE & IMMUTABLE AUDIT LEDGER ==="
[[ -d "$TARGET/.git" ]] || fail "target Git repository not found: $TARGET"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || fail "$PYTHON_BIN is required"
cd "$TARGET"
DIRTY="$(git status --porcelain --untracked-files=all | grep -Ev '^\?\? (backend/)?\.venv([^/]*)?/' || true)"
if [[ -n "$DIRTY" ]]; then git status --short; fail "target working tree has source changes"; fi
rm -rf backend/.venv backend/.venv-* .venv .venv-*
grep -q 'APP_VERSION = "3.14.0"' backend/app/services/decision_service.py || fail "expected v3.14.0 source as v3.15 baseline"

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

echo "=== FULL BACKEND + IMMUTABLE AUDIT LEDGER VALIDATION ==="
cd backend
PYTHONPATH=. python -m pytest -q
rm -f "$VENV/v3150-schema.db"
SCDS_DATABASE_URL="sqlite+pysqlite:///$VENV/v3150-schema.db" alembic upgrade head
python - "$VENV/v3150-schema.db" <<'PY'
import sys
from sqlalchemy import create_engine, inspect, text
eng=create_engine('sqlite+pysqlite:///'+sys.argv[1])
with eng.connect() as c:
    rev=c.execute(text('select version_num from alembic_version')).scalar_one()
    triggers={r[0] for r in c.execute(text("select name from sqlite_master where type='trigger' and tbl_name='decision_audit_events'"))}
tables=[t for t in inspect(eng).get_table_names() if t!='alembic_version']
assert rev=='0003_v3150_event_ledger',rev
assert len(tables)==27,len(tables)
assert 'decision_audit_events' in tables,tables
assert {'trg_decision_audit_events_no_update','trg_decision_audit_events_no_delete'} <= triggers,triggers
print('PASS: v3.15 Alembic upgrade reaches 0003_v3150_event_ledger with 27 tables and append-only ledger triggers')
PY
cd ..
python scripts/test_release.py
php -l wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php
if command -v node >/dev/null 2>&1; then
  node --check wordpress-plugin/sustainable-catalyst-decision-studio/assets/js/scds-decision-studio.js
  node --check wordpress-plugin/sustainable-catalyst-decision-studio/assets/js/scds-offline-workspace.js
fi
bash -n deploy/contabo/deploy_decision_studio_v3_15_0_from_macos.sh
bash -n deploy/contabo/upgrade_decision_studio_backend_v3_15_0_contabo.sh
bash -n scripts/build_release.sh

echo "=== GIT COMMIT / PUSH / TAG ==="
find . -type d \( -name '__pycache__' -o -name '.pytest_cache' \) -prune -exec rm -rf {} +
find . -type f -name '*.pyc' -delete
git add -A
if ! git diff --cached --quiet; then git commit -m "Decision Studio v3.15.0 — Decision Event Store & Immutable Audit Ledger"; else echo "No new source changes to commit."; fi
git push origin main
if git rev-parse -q --verify refs/tags/v3.15.0 >/dev/null; then
  [[ "$(git rev-list -n1 v3.15.0)" == "$(git rev-parse HEAD)" ]] || fail "tag v3.15.0 already exists on a different commit"
else
  git tag -a v3.15.0 -m "Decision Studio v3.15.0 — Decision Event Store & Immutable Audit Ledger"
fi
git push origin v3.15.0

echo "=== BUILD RELEASE DISTRIBUTABLES ==="
mkdir -p "$OUT"
PYTHON_BIN="$VENV/venv/bin/python" bash scripts/build_release.sh "$OUT"
cp deploy/contabo/upgrade_decision_studio_backend_v3_15_0_contabo.sh "$OUT/"
cp deploy/contabo/deploy_decision_studio_v3_15_0_from_macos.sh "$OUT/"
cp V3150_DECISION_EVENT_STORE_IMMUTABLE_AUDIT_LEDGER_COMMANDS.txt "$OUT/"
chmod +x "$OUT/upgrade_decision_studio_backend_v3_15_0_contabo.sh" "$OUT/deploy_decision_studio_v3_15_0_from_macos.sh"

echo "=== FINAL SOURCE STATE ==="
git status --short
git log -1 --oneline
git tag --points-at HEAD

echo "PASS - Decision Studio v3.15.0 applied, validated, migrated in test, pushed, tagged, and packaged"
echo "NEXT: cd $OUT && ./deploy_decision_studio_v3_15_0_from_macos.sh"
