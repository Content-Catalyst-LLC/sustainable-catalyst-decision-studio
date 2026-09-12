#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="2.3.1"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v2.3.1.zip}"
ROOT="/opt/sustainable-catalyst/decision-studio"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
BACKUP_ROOT="/opt/sustainable-catalyst/backups"
CONTAINER="sc-decision-studio"
SERVICE="decision-studio"
PORT="8089"
PUBLIC_URL="${SCDS_PUBLIC_URL:-https://decision-studio-api.sustainablecatalyst.com}"
TMP="$(mktemp -d /tmp/sc-decision-studio-v231.XXXXXX)"
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
[[ -n "$SRC" && -f "$SRC/app/main.py" && -f "$SRC/app/tradeoff_matrix.py" && -f "$SRC/app/evidence_bundle.py" && -f "$SRC/app/energy_runtime_consumer.py" && -f "$SRC/Dockerfile" ]] || fail "v2.3.1 backend payload is incomplete"
grep -q 'APP_VERSION = "2.3.1"' "$SRC/app/main.py" || fail "payload is not Decision Studio v2.3.1"
grep -q 'scds-v2.3.1-criteria-alternatives-tradeoff-matrix' "$SRC/app/main.py" || fail "v2.3.1 build fingerprint missing"

mkdir -p "$BACKUP_ROOT"
stamp="$(date +%Y%m%d-%H%M%S)"
backup="$BACKUP_ROOT/decision-studio-before-v2.3.1-$stamp.tgz"

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
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-decision-studio:)[^\s#]+', r'\g<1>2.3.1', s)
s=re.sub(r'(?m)^(\s*SCDS_BUILD_FINGERPRINT:\s*).+$', r'\g<1>scds-v2.3.1-criteria-alternatives-tradeoff-matrix', s)
s=re.sub(r'(?m)^(\s*SCDS_SOURCE_COMMIT:\s*).+$', r'\g<1>release-v2.3.1', s)
p.write_text(s)
PY

cd "$ROOT"
docker compose config --quiet

echo "=== BUILD v2.3.1 ==="
docker compose build "$SERVICE"
docker compose up -d --force-recreate "$SERVICE"

health=""
for _ in $(seq 1 60); do
  if health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null)"; then
    if python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]); r=x.get('release',{})
assert x.get('ok') is True and x.get('ready') is True
assert x.get('version') == '2.3.1'
assert x.get('build_fingerprint') == 'scds-v2.3.1-criteria-alternatives-tradeoff-matrix'
assert r.get('criteria_set_schema') == 'scds-criteria-set/1.0'
assert r.get('tradeoff_matrix_schema') == 'scds-tradeoff-matrix/1.0'
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
assert x.get('version') == '2.3.1', x
assert x.get('service') == 'sustainable-catalyst-decision-studio', x
assert x.get('build_fingerprint') == 'scds-v2.3.1-criteria-alternatives-tradeoff-matrix', x
assert r.get('decision_object_schema') == 'scds-decision-object/1.0', r
assert r.get('evidence_bundle_schema') == 'scds-evidence-bundle/1.0', r
assert r.get('criteria_set_schema') == 'scds-criteria-set/1.0', r
assert r.get('alternatives_set_schema') == 'scds-alternatives-set/1.0', r
assert r.get('tradeoff_matrix_schema') == 'scds-tradeoff-matrix/1.0', r
assert r.get('tradeoff_diagnostics_schema') == 'scds-tradeoff-diagnostics/1.0', r
assert r.get('compatibility',{}).get('automatic_winner_selection') is False, r
assert r.get('compatibility',{}).get('automatic_recommendation') is False, r
assert r.get('compatibility',{}).get('energy_systems_runtime_consumer') is True, r
assert r.get('compatibility',{}).get('energy_runtime_consumer_version') == '2.3.0', r
print('PASS: internal health identifies Decision Studio backend v2.3.1 with Energy v2.3.0 consumer preserved')
PY

echo "=== v2.3.1 TRADEOFF MATRIX SMOKE TEST ==="
payload='{"packet":{"decision_packet_id":"VPS-V231","project":{"decision_question":"Which option?"}},"criteria":[{"criterion_id":"cost","name":"Cost","weight":40,"direction":"minimize","scale":{"min":0,"max":100}},{"criterion_id":"impact","name":"Impact","weight":60,"direction":"maximize","scale":{"min":0,"max":10}}],"alternatives":[{"alternative_id":"a","name":"Option A"},{"alternative_id":"b","name":"Option B"}],"evaluations":[{"alternative_id":"a","criterion_id":"cost","value":20,"review_status":"reviewed"},{"alternative_id":"a","criterion_id":"impact","value":8,"review_status":"reviewed"},{"alternative_id":"b","criterion_id":"cost","value":60,"review_status":"reviewed"},{"alternative_id":"b","criterion_id":"impact","value":9,"review_status":"reviewed"}]}'
built="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$payload" "http://127.0.0.1:${PORT}/tradeoff-matrix/build")"
python3 - "$built" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); m=x['tradeoff_matrix']; d=m['diagnostics']
assert x.get('version') == '2.3.1'
assert m.get('schema') == 'scds-tradeoff-matrix/1.0'
assert m['criteria_set']['schema'] == 'scds-criteria-set/1.0'
assert m['alternatives_set']['schema'] == 'scds-alternatives-set/1.0'
assert d['matrix_coverage_percent'] == 100.0
assert d['complete'] is True
assert len(m['alternative_summaries']) == 2
assert all('not an automatic recommendation' in s['score_interpretation'] for s in m['alternative_summaries'])
print('PASS: criteria, alternatives, weighted comparison, and matrix diagnostics')
PY

attached="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$payload" "http://127.0.0.1:${PORT}/decision-object/tradeoffs")"
python3 - "$attached" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); obj=x['decision_object']; m=x['tradeoff_matrix']
assert obj['schema'] == 'scds-decision-object/1.0'
assert obj['provenance']['source_packet_schema'] == 'scds-decision-packet/2.0'
assert obj['tradeoff_matrices'][0]['schema'] == 'scds-tradeoff-matrix/1.0'
assert len(obj['criteria']) == 2 and len(obj['alternatives']) == 2
assert obj['provenance']['records'][-1]['action'] == 'tradeoff_matrix_attached'
print('PASS: Tradeoff Matrix attaches to the Unified Decision Object')
PY

echo "=== PRESERVED v2.3.0 ENERGY RUNTIME CONSUMER SMOKE TEST ==="
energy_framework="$(curl -fsS "http://127.0.0.1:${PORT}/v1/energy-runtime/consumer")"
python3 - "$energy_framework" <<'PY'
import json,sys
x=json.loads(sys.argv[1])
assert x.get('ok') is True, x
assert x.get('consumer_version') == '2.3.0', x
assert x.get('consumer_contract') == 'sc-energy-runtime-decision-studio-handoff/1.0', x
assert x.get('capabilities',{}).get('automatic_ranking') is False, x
assert x.get('capabilities',{}).get('automatic_recommendation') is False, x
print('PASS: Energy Systems Runtime Consumer v2.3.0 remains registered')
PY

energy_payload='{"schema":"sc-energy-runtime-handoff/1.0","version":"1.2.0","packet":{"handoff_id":"es-v231-smoke","source":{"product":"Library","subsystem":"Energy Systems Intelligence","version":"1.2.0"},"target":{"key":"decision-studio","product":"Decision Studio","consumer_contract":"sc-energy-runtime-decision-studio-handoff/1.0"},"contract_refs":["integrated-energy-study-contract"],"payload":{"identity":{"study_id":"study:v231-smoke","question":"Compare energy pathways"},"decision":{},"economics":{},"sustainability_indicators":[],"global_context":{},"uncertainty":[],"provenance":[{"source_ref":"source:v231-smoke"}],"review":{}}}}'
energy_receipt="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$energy_payload" "http://127.0.0.1:${PORT}/v1/energy-runtime/consume")"
python3 - "$energy_receipt" <<'PY'
import json,sys
x=json.loads(sys.argv[1])
assert x.get('accepted') is True, x
assert x.get('consumer',{}).get('app_version') == '2.3.0', x
assert x.get('execution',{}).get('performed') is False, x
assert x.get('persistence',{}).get('performed') is False, x
assert len(x.get('receipt_fingerprint','')) == 64, x
print('PASS: Energy Systems handoff acceptance remains compatible and bounded')
PY

if [[ -n "$PUBLIC_URL" ]]; then
  echo "=== PUBLIC CADDY CHECK ==="
  if public_health="$(curl -fsS --max-time 20 "${PUBLIC_URL%/}/health" 2>/dev/null)"; then
    python3 - "$public_health" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); assert x.get('ok') is True and x.get('version') == '2.3.1', x
print('PASS: public Decision Studio API returns v2.3.1')
PY
  else
    echo "WARNING: public Caddy check did not answer; internal v2.3.1 verification passed."
  fi
fi

echo "=== FINAL CONTAINER ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v2.3.1 deployed and verified on port 8089"
echo "Backup: $backup"
