#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="2.2.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v2.2.0.zip}"
ROOT="/opt/sustainable-catalyst/decision-studio"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
BACKUP_ROOT="/opt/sustainable-catalyst/backups"
CONTAINER="sc-decision-studio"
SERVICE="decision-studio"
PORT="8089"
PUBLIC_URL="${SCDS_PUBLIC_URL:-https://decision-studio-api.sustainablecatalyst.com}"
TMP="$(mktemp -d /tmp/sc-decision-studio-v220.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

fail(){ echo "ERROR: $*" >&2; exit 1; }
pass(){ echo "PASS: $*"; }

for cmd in unzip rsync docker curl python3 tar; do command -v "$cmd" >/dev/null || fail "$cmd is required"; done
[[ -f "$ARCHIVE" ]] || fail "backend ZIP not found: $ARCHIVE"
[[ -d "$ROOT" && -d "$LIVE_BACKEND" && -f "$COMPOSE" ]] || fail "Decision Studio runtime root/backend/compose is incomplete"
docker network inspect sc-internal >/dev/null 2>&1 || fail "Docker network sc-internal is missing"
unzip -tq "$ARCHIVE" >/dev/null || fail "invalid backend ZIP"

unzip -q "$ARCHIVE" -d "$TMP/package"
SRC="$(find "$TMP/package" -type f -path '*/backend/app/main.py' -printf '%h/..\n' | head -1 | xargs -r realpath)"
[[ -n "$SRC" && -f "$SRC/app/main.py" && -f "$SRC/app/evidence_bundle.py" && -f "$SRC/Dockerfile" ]] || fail "v2.2.0 backend payload is incomplete"
grep -q 'APP_VERSION = "2.2.0"' "$SRC/app/main.py" || fail "payload is not Decision Studio v2.2.0"
grep -q 'scds-v2.2.0-evidence-source-bundles' "$SRC/app/main.py" || fail "v2.2.0 build fingerprint missing"

mkdir -p "$BACKUP_ROOT"
stamp="$(date +%Y%m%d-%H%M%S)"
backup="$BACKUP_ROOT/decision-studio-before-v2.2.0-$stamp.tgz"

echo "=== CURRENT DECISION STUDIO ==="
docker ps -a --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' || true
curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null | python3 -m json.tool || true

echo "=== BACKUP ==="
tar -C "$(dirname "$ROOT")" -czf "$backup" "$(basename "$ROOT")"
echo "$backup"

for envfile in .env .env.production; do [[ -f "$LIVE_BACKEND/$envfile" ]] && cp -a "$LIVE_BACKEND/$envfile" "$TMP/$envfile"; done
cp -a "$COMPOSE" "$TMP/compose.before.yml"

rsync -a --delete --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='*.pyc' --exclude='.env' --exclude='.env.production' "$SRC/" "$LIVE_BACKEND/"
for envfile in .env .env.production; do [[ -f "$TMP/$envfile" ]] && cp -a "$TMP/$envfile" "$LIVE_BACKEND/$envfile"; done

python3 - "$COMPOSE" <<'PY'
from pathlib import Path
import re, sys
p=Path(sys.argv[1]); s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-decision-studio:)[^\s#]+', r'\g<1>2.2.0', s)
s=re.sub(r'(?m)^(\s*SCDS_BUILD_FINGERPRINT:\s*).+$', r'\g<1>scds-v2.2.0-evidence-source-bundles', s)
s=re.sub(r'(?m)^(\s*SCDS_SOURCE_COMMIT:\s*).+$', r'\g<1>release-v2.2.0', s)
p.write_text(s)
PY

cd "$ROOT"
docker compose config --quiet

echo "=== BUILD v2.2.0 ==="
docker compose build "$SERVICE"
docker compose up -d --force-recreate "$SERVICE"

health=""
for _ in $(seq 1 60); do
  if health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null)"; then
    if python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]); r=x.get('release',{})
assert x.get('ok') is True and x.get('ready') is True
assert x.get('version') == '2.2.0'
assert x.get('build_fingerprint') == 'scds-v2.2.0-evidence-source-bundles'
assert r.get('evidence_bundle_schema') == 'scds-evidence-bundle/1.0'
assert r.get('source_bundle_schema') == 'scds-source-bundle/1.0'
PY
    then break; fi
  fi
  sleep 2
done
[[ -n "$health" ]] || { docker logs --tail=200 "$CONTAINER" >&2 || true; fail "backend did not answer /health"; }

python3 - "$health" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); r=x.get('release',{})
assert x.get('ok') is True and x.get('ready') is True, x
assert x.get('version') == '2.2.0', x
assert x.get('service') == 'sustainable-catalyst-decision-studio', x
assert x.get('build_fingerprint') == 'scds-v2.2.0-evidence-source-bundles', x
assert r.get('decision_object_schema') == 'scds-decision-object/1.0', r
assert r.get('platform_context_schema') == 'scds-platform-context/1.0', r
assert r.get('evidence_bundle_schema') == 'scds-evidence-bundle/1.0', r
assert r.get('source_bundle_schema') == 'scds-source-bundle/1.0', r
assert r.get('compatibility',{}).get('packet_schema_breaking_changes') is False, r
assert r.get('compatibility',{}).get('automatic_truth_verification') is False, r
print('PASS: internal health identifies Decision Studio backend v2.2.0')
PY

echo "=== v2.2.0 EVIDENCE SMOKE TEST ==="
payload='{"packet":{"decision_packet_id":"VPS-V220","project":{"decision_question":"Which option?"}},"sources":[{"source_id":"src-smoke","title":"Smoke source","review_status":"reviewed"}],"evidence":[{"evidence_id":"ev-smoke","claim":"Smoke-test claim","stance":"supports","source_ids":["src-smoke"],"review_status":"reviewed"}]}'
built="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$payload" "http://127.0.0.1:${PORT}/evidence-bundle/build")"
python3 - "$built" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); b=x['evidence_bundle']; c=b['coverage']
assert x.get('version') == '2.2.0'
assert b.get('schema') == 'scds-evidence-bundle/1.0'
assert b['source_bundle']['schema'] == 'scds-source-bundle/1.0'
assert c['citation_coverage_percent'] == 100.0
assert c['review_ready'] is True
print('PASS: Evidence Bundle build, source linking, coverage, and review diagnostics')
PY

attached="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$payload" "http://127.0.0.1:${PORT}/decision-object/evidence")"
python3 - "$attached" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); obj=x['decision_object']
assert obj['schema'] == 'scds-decision-object/1.0'
assert obj['provenance']['source_packet_schema'] == 'scds-decision-packet/2.0'
assert obj['evidence_bundles'][0]['schema'] == 'scds-evidence-bundle/1.0'
assert obj['evidence'][0]['evidence_id'] == 'ev-smoke'
print('PASS: Evidence Bundle attaches to the Unified Decision Object')
PY

if [[ -n "$PUBLIC_URL" ]]; then
  echo "=== PUBLIC CADDY CHECK ==="
  if public_health="$(curl -fsS --max-time 20 "${PUBLIC_URL%/}/health" 2>/dev/null)"; then
    python3 - "$public_health" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); assert x.get('ok') is True and x.get('version') == '2.2.0', x
print('PASS: public Decision Studio API returns v2.2.0')
PY
  else
    echo "WARNING: public Caddy check did not answer; internal v2.2.0 verification passed."
  fi
fi

echo "=== FINAL CONTAINER ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v2.2.0 deployed and verified on port 8089"
echo "Backup: $backup"
