#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="2.4.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v2.4.0.zip}"
ROOT="/opt/sustainable-catalyst/decision-studio"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
BACKUP_ROOT="/opt/sustainable-catalyst/backups"
CONTAINER="sc-decision-studio"
SERVICE="decision-studio"
PORT="8089"
PUBLIC_URL="${SCDS_PUBLIC_URL:-https://decision-studio-api.sustainablecatalyst.com}"
TMP="$(mktemp -d /tmp/sc-decision-studio-v240.XXXXXX)"
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
[[ -n "$SRC" && -f "$SRC/app/main.py" && -f "$SRC/app/uncertainty_confidence.py" && -f "$SRC/app/tradeoff_matrix.py" && -f "$SRC/app/evidence_bundle.py" && -f "$SRC/app/energy_runtime_consumer.py" && -f "$SRC/Dockerfile" ]] || fail "v2.4.0 backend payload is incomplete"
grep -q 'APP_VERSION = "2.4.0"' "$SRC/app/main.py" || fail "payload is not Decision Studio v2.4.0"
grep -q 'scds-v2.4.0-uncertainty-sensitivity-confidence' "$SRC/app/main.py" || fail "v2.4.0 build fingerprint missing"

mkdir -p "$BACKUP_ROOT"
stamp="$(date +%Y%m%d-%H%M%S)"
backup="$BACKUP_ROOT/decision-studio-before-v2.4.0-$stamp.tgz"

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
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-decision-studio:)[^\s#]+', r'\g<1>2.4.0', s)
s=re.sub(r'(?m)^(\s*SCDS_BUILD_FINGERPRINT:\s*).+$', r'\g<1>scds-v2.4.0-uncertainty-sensitivity-confidence', s)
s=re.sub(r'(?m)^(\s*SCDS_SOURCE_COMMIT:\s*).+$', r'\g<1>release-v2.4.0', s)
p.write_text(s)
PY

cd "$ROOT"
docker compose config --quiet

echo "=== BUILD v2.4.0 ==="
docker compose build "$SERVICE"
docker compose up -d --force-recreate "$SERVICE"

health=""
for _ in $(seq 1 60); do
  if health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null)"; then
    if python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]); r=x.get('release',{})
assert x.get('ok') is True and x.get('ready') is True
assert x.get('version') == '2.4.0'
assert x.get('build_fingerprint') == 'scds-v2.4.0-uncertainty-sensitivity-confidence'
assert r.get('uncertainty_register_schema') == 'scds-uncertainty-register/1.0'
assert r.get('sensitivity_analysis_schema') == 'scds-sensitivity-analysis/1.0'
assert r.get('confidence_assessment_schema') == 'scds-confidence-assessment/1.0'
PY
    then break; fi
  fi
  sleep 2
done
[[ -n "$health" ]] || { docker logs --tail=200 "$CONTAINER" >&2 || true; fail "backend did not answer /health"; }

python3 - "$health" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); r=x.get('release',{}); c=r.get('compatibility',{})
assert x.get('ok') is True and x.get('ready') is True, x
assert x.get('version') == '2.4.0', x
assert x.get('service') == 'sustainable-catalyst-decision-studio', x
assert x.get('build_fingerprint') == 'scds-v2.4.0-uncertainty-sensitivity-confidence', x
assert r.get('tradeoff_matrix_schema') == 'scds-tradeoff-matrix/1.0', r
assert r.get('uncertainty_register_schema') == 'scds-uncertainty-register/1.0', r
assert r.get('sensitivity_analysis_schema') == 'scds-sensitivity-analysis/1.0', r
assert r.get('confidence_assessment_schema') == 'scds-confidence-assessment/1.0', r
assert c.get('automatic_winner_selection') is False, c
assert c.get('automatic_recommendation') is False, c
assert c.get('confidence_is_probability_of_correctness') is False, c
assert c.get('energy_systems_runtime_consumer') is True, c
assert c.get('energy_runtime_consumer_version') == '2.3.0', c
print('PASS: internal health identifies Decision Studio backend v2.4.0 with Energy v2.3.0 consumer preserved')
PY

echo "=== v2.4.0 UNCERTAINTY / SENSITIVITY / CONFIDENCE SMOKE TEST ==="
matrix_payload='{"packet":{"decision_packet_id":"VPS-V240","project":{"decision_question":"Which option is robust?"}},"criteria":[{"criterion_id":"cost","name":"Cost","weight":40,"direction":"minimize","scale":{"min":0,"max":100}},{"criterion_id":"impact","name":"Impact","weight":60,"direction":"maximize","scale":{"min":0,"max":10}}],"alternatives":[{"alternative_id":"a","name":"Option A"},{"alternative_id":"b","name":"Option B"}],"evaluations":[{"evaluation_id":"a-cost","alternative_id":"a","criterion_id":"cost","value":20,"evidence_refs":["src-cost"],"review_status":"reviewed"},{"evaluation_id":"a-impact","alternative_id":"a","criterion_id":"impact","value":8,"evidence_refs":["src-impact"],"review_status":"reviewed"},{"evaluation_id":"b-cost","alternative_id":"b","criterion_id":"cost","value":60,"evidence_refs":["src-cost"],"review_status":"reviewed"},{"evaluation_id":"b-impact","alternative_id":"b","criterion_id":"impact","value":9,"evidence_refs":["src-impact"],"review_status":"reviewed"}]}'
built="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$matrix_payload" "http://127.0.0.1:${PORT}/tradeoff-matrix/build")"
matrix="$(python3 - "$built" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); m=x['tradeoff_matrix']; assert m['diagnostics']['matrix_coverage_percent']==100.0; print(json.dumps(m,separators=(',',':')))
PY
)"
analysis_payload="$(python3 - "$matrix" <<'PY'
import json,sys
m=json.loads(sys.argv[1])
p={'tradeoffMatrix':m,'uncertainties':[{'uncertainty_id':'u-a-cost','target_type':'evaluation','target_id':'a-cost','parameter':'value','lower':10,'upper':45,'review_status':'reviewed','source_refs':['src-cost']},{'uncertainty_id':'u-a-impact','target_type':'evaluation','target_id':'a-impact','parameter':'value','lower':6,'upper':9,'review_status':'reviewed','source_refs':['src-impact']}],'sensitivityConfig':{'weight_perturbation_percent':25}}
print(json.dumps(p,separators=(',',':')))
PY
)"
confidence="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$analysis_payload" "http://127.0.0.1:${PORT}/confidence-assessment/build")"
python3 - "$confidence" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); u=x['uncertainty_register']; s=x['sensitivity_analysis']; c=x['confidence_assessment']
assert x.get('version') == '2.4.0'
assert u.get('schema') == 'scds-uncertainty-register/1.0'
assert u['diagnostics']['characterization_coverage_percent'] == 100.0
assert s.get('schema') == 'scds-sensitivity-analysis/1.0'
assert s['diagnostics']['weight_tests'] == 4
assert s['diagnostics']['uncertainty_tests'] == 4
assert len(s['alternative_score_envelopes']) == 2
assert c.get('schema') == 'scds-confidence-assessment/1.0'
assert 0 <= c['process_confidence_index'] <= 100
assert 'probability' in c['boundary'].lower()
print('PASS: uncertainty register, deterministic sensitivity, score envelopes, and bounded process confidence')
PY

attached="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$analysis_payload" "http://127.0.0.1:${PORT}/decision-object/uncertainty-confidence")"
python3 - "$attached" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); obj=x['decision_object']
assert obj['schema'] == 'scds-decision-object/1.0'
assert obj['uncertainty_registers'][-1]['schema'] == 'scds-uncertainty-register/1.0'
assert obj['sensitivity_analyses'][-1]['schema'] == 'scds-sensitivity-analysis/1.0'
assert obj['confidence_assessments'][-1]['schema'] == 'scds-confidence-assessment/1.0'
assert obj['provenance']['records'][-1]['action'] == 'uncertainty_sensitivity_confidence_attached'
print('PASS: v2.4.0 analysis attaches to the Unified Decision Object')
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

energy_payload='{"schema":"sc-energy-runtime-handoff/1.0","version":"1.2.0","packet":{"handoff_id":"es-v240-smoke","source":{"product":"Library","subsystem":"Energy Systems Intelligence","version":"1.2.0"},"target":{"key":"decision-studio","product":"Decision Studio","consumer_contract":"sc-energy-runtime-decision-studio-handoff/1.0"},"contract_refs":["integrated-energy-study-contract"],"payload":{"identity":{"study_id":"study:v240-smoke","question":"Compare energy pathways"},"decision":{},"economics":{},"sustainability_indicators":[],"global_context":{},"uncertainty":[],"provenance":[{"source_ref":"source:v240-smoke"}],"review":{}}}}'
energy_receipt="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$energy_payload" "http://127.0.0.1:${PORT}/v1/energy-runtime/consume")"
python3 - "$energy_receipt" <<'PY'
import json,sys
x=json.loads(sys.argv[1])
assert x.get('accepted') is True, x
assert x.get('consumer',{}).get('app_version') == '2.3.0', x
assert x.get('execution',{}).get('performed') is False, x
assert x.get('persistence',{}).get('performed') is False, x
print('PASS: Energy Systems handoff acceptance remains compatible and bounded')
PY

if [[ -n "$PUBLIC_URL" ]]; then
  echo "=== PUBLIC CADDY CHECK ==="
  if public_health="$(curl -fsS --max-time 20 "${PUBLIC_URL%/}/health" 2>/dev/null)"; then
    python3 - "$public_health" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); assert x.get('ok') is True and x.get('version') == '2.4.0', x
print('PASS: public Decision Studio API returns v2.4.0')
PY
  else
    echo "WARNING: public Caddy check did not answer; internal v2.4.0 verification passed."
  fi
fi

echo "=== FINAL CONTAINER ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v2.4.0 deployed and verified on port 8089"
echo "Backup: $backup"
