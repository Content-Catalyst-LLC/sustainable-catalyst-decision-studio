#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="2.5.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v2.5.0.zip}"
ROOT="/opt/sustainable-catalyst/decision-studio"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
BACKUP_ROOT="/opt/sustainable-catalyst/backups"
CONTAINER="sc-decision-studio"
SERVICE="decision-studio"
PORT="8089"
PUBLIC_URL="${SCDS_PUBLIC_URL:-https://decision-studio-api.sustainablecatalyst.com}"
TMP="$(mktemp -d /tmp/sc-decision-studio-v250.XXXXXX)"
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
[[ -n "$SRC" && -f "$SRC/app/main.py" && -f "$SRC/app/scenario_stress.py" && -f "$SRC/app/uncertainty_confidence.py" && -f "$SRC/app/tradeoff_matrix.py" && -f "$SRC/app/evidence_bundle.py" && -f "$SRC/app/energy_runtime_consumer.py" && -f "$SRC/Dockerfile" ]] || fail "v2.5.0 backend payload is incomplete"
grep -q 'APP_VERSION = "2.5.0"' "$SRC/app/main.py" || fail "payload is not Decision Studio v2.5.0"
grep -q 'scds-v2.5.0-scenario-comparison-stress-testing' "$SRC/app/main.py" || fail "v2.5.0 build fingerprint missing"

mkdir -p "$BACKUP_ROOT"
stamp="$(date +%Y%m%d-%H%M%S)"
backup="$BACKUP_ROOT/decision-studio-before-v2.5.0-$stamp.tgz"

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
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-decision-studio:)[^\s#]+', r'\g<1>2.5.0', s)
s=re.sub(r'(?m)^(\s*SCDS_BUILD_FINGERPRINT:\s*).+$', r'\g<1>scds-v2.5.0-scenario-comparison-stress-testing', s)
s=re.sub(r'(?m)^(\s*SCDS_SOURCE_COMMIT:\s*).+$', r'\g<1>release-v2.5.0', s)
p.write_text(s)
PY

cd "$ROOT"
docker compose config --quiet

echo "=== BUILD v2.5.0 ==="
docker compose build "$SERVICE"
docker compose up -d --force-recreate "$SERVICE"

health=""
for _ in $(seq 1 60); do
  if health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null)"; then
    if python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]); r=x.get('release',{})
assert x.get('ok') is True and x.get('ready') is True
assert x.get('version') == '2.5.0'
assert x.get('build_fingerprint') == 'scds-v2.5.0-scenario-comparison-stress-testing'
assert r.get('scenario_set_schema') == 'scds-scenario-set/1.0'
assert r.get('scenario_comparison_schema') == 'scds-scenario-comparison/1.0'
assert r.get('stress_test_suite_schema') == 'scds-stress-test-suite/1.0'
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
assert x.get('version') == '2.5.0', x
assert x.get('service') == 'sustainable-catalyst-decision-studio', x
assert x.get('build_fingerprint') == 'scds-v2.5.0-scenario-comparison-stress-testing', x
assert r.get('tradeoff_matrix_schema') == 'scds-tradeoff-matrix/1.0', r
assert r.get('uncertainty_register_schema') == 'scds-uncertainty-register/1.0', r
assert r.get('scenario_set_schema') == 'scds-scenario-set/1.0', r
assert r.get('scenario_comparison_schema') == 'scds-scenario-comparison/1.0', r
assert r.get('stress_test_suite_schema') == 'scds-stress-test-suite/1.0', r
assert c.get('automatic_winner_selection') is False, c
assert c.get('automatic_recommendation') is False, c
assert c.get('confidence_is_probability_of_correctness') is False, c
assert c.get('scenario_likelihood_inference') is False, c
assert c.get('stress_test_pass_implies_approval') is False, c
assert c.get('energy_systems_runtime_consumer') is True, c
assert c.get('energy_runtime_consumer_version') == '2.3.0', c
print('PASS: internal health identifies Decision Studio backend v2.5.0 with v2.4 uncertainty and Energy v2.3.0 preserved')
PY

echo "=== v2.5.0 SCENARIO COMPARISON / STRESS TEST SMOKE TEST ==="
matrix_payload='{"packet":{"decision_packet_id":"VPS-V250","project":{"decision_question":"Which option stays robust across conditions?"}},"criteria":[{"criterion_id":"cost","name":"Cost","weight":40,"direction":"minimize","scale":{"min":0,"max":100}},{"criterion_id":"impact","name":"Impact","weight":60,"direction":"maximize","scale":{"min":0,"max":10}}],"alternatives":[{"alternative_id":"a","name":"Option A"},{"alternative_id":"b","name":"Option B"}],"evaluations":[{"evaluation_id":"a-cost","alternative_id":"a","criterion_id":"cost","value":20,"evidence_refs":["src-cost"],"review_status":"reviewed"},{"evaluation_id":"a-impact","alternative_id":"a","criterion_id":"impact","value":8,"evidence_refs":["src-impact"],"review_status":"reviewed"},{"evaluation_id":"b-cost","alternative_id":"b","criterion_id":"cost","value":60,"evidence_refs":["src-cost"],"review_status":"reviewed"},{"evaluation_id":"b-impact","alternative_id":"b","criterion_id":"impact","value":9,"evidence_refs":["src-impact"],"review_status":"reviewed"}]}'
built="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$matrix_payload" "http://127.0.0.1:${PORT}/tradeoff-matrix/build")"
matrix="$(python3 - "$built" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); m=x['tradeoff_matrix']; assert m['diagnostics']['matrix_coverage_percent']==100.0; print(json.dumps(m,separators=(',',':')))
PY
)"
scenario_payload="$(python3 - "$matrix" <<'PY'
import json,sys
m=json.loads(sys.argv[1])
p={
 'tradeoffMatrix':m,
 'scenarios':[
   {'scenario_id':'baseline','name':'Baseline','kind':'baseline','review_status':'reviewed'},
   {'scenario_id':'cost-pressure','name':'Cost pressure','kind':'downside','evaluation_overrides':[{'evaluation_id':'a-cost','value':55}],'review_status':'reviewed'},
   {'scenario_id':'combined-stress','name':'Combined stress','kind':'stress','evaluation_overrides':[{'evaluation_id':'a-cost','value':90}],'weight_overrides':[{'criterion_id':'cost','weight':55},{'criterion_id':'impact','weight':45}],'review_status':'reviewed'}
 ],
 'stressConfig':{'max_allowed_score_drop':15,'max_allowed_threshold_violations':0,'require_complete_matrix':True,'minimum_process_confidence':0}
}
print(json.dumps(p,separators=(',',':')))
PY
)"
comparison="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$scenario_payload" "http://127.0.0.1:${PORT}/scenario-analysis/compare")"
python3 - "$comparison" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); ss=x['scenario_set']; c=x['scenario_comparison']
assert x.get('version') == '2.5.0', x
assert ss.get('schema') == 'scds-scenario-set/1.0', ss
assert ss['diagnostics']['scenario_count'] == 3, ss
assert ss['diagnostics']['stress_scenario_count'] == 1, ss
assert c.get('schema') == 'scds-scenario-comparison/1.0', c
assert c['diagnostics']['scenario_count'] == 3, c
assert c['diagnostics']['max_score_swing'] > 0, c
assert 'combined-stress' in c['diagnostics']['ordering_change_scenario_ids'], c
assert len(c['alternative_score_ranges']) == 2, c
assert 'winner' not in c and 'recommended_option' not in c, c
assert 'does not predict' in c['boundary'].lower(), c
print('PASS: named scenarios produce cross-scenario score ranges and visible ordering changes without winner selection')
PY

stress="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$scenario_payload" "http://127.0.0.1:${PORT}/stress-test-suite/run")"
python3 - "$stress" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); s=x['stress_test_suite']
assert x.get('version') == '2.5.0', x
assert s.get('schema') == 'scds-stress-test-suite/1.0', s
assert s['diagnostics']['test_count'] == 1, s
assert s['diagnostics']['failed_count'] == 1, s
assert any(f.get('failure_code') == 'score_drop_limit_exceeded' for f in s['failure_modes']), s
assert 'not approval' in s['boundary'].lower(), s
print('PASS: stress testing exposes explicit failure modes and does not imply approval')
PY

attached="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$scenario_payload" "http://127.0.0.1:${PORT}/decision-object/scenario-stress")"
python3 - "$attached" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); obj=x['decision_object']
assert obj['schema'] == 'scds-decision-object/1.0', obj
assert obj['scenario_sets'][-1]['schema'] == 'scds-scenario-set/1.0', obj
assert obj['scenario_comparisons'][-1]['schema'] == 'scds-scenario-comparison/1.0', obj
assert obj['stress_test_suites'][-1]['schema'] == 'scds-stress-test-suite/1.0', obj
assert obj['provenance']['records'][-1]['action'] == 'scenario_comparison_stress_tests_attached', obj
print('PASS: v2.5.0 scenario and stress artifacts attach to the Unified Decision Object')
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

energy_payload='{"schema":"sc-energy-runtime-handoff/1.0","version":"1.2.0","packet":{"handoff_id":"es-v250-smoke","source":{"product":"Library","subsystem":"Energy Systems Intelligence","version":"1.2.0"},"target":{"key":"decision-studio","product":"Decision Studio","consumer_contract":"sc-energy-runtime-decision-studio-handoff/1.0"},"contract_refs":["integrated-energy-study-contract"],"payload":{"identity":{"study_id":"study:v250-smoke","question":"Compare energy pathways"},"decision":{},"economics":{},"sustainability_indicators":[],"global_context":{},"uncertainty":[],"provenance":[{"source_ref":"source:v250-smoke"}],"review":{}}}}'
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
x=json.loads(sys.argv[1]); assert x.get('ok') is True and x.get('version') == '2.5.0', x
print('PASS: public Decision Studio API returns v2.5.0')
PY
  else
    echo "WARNING: public Caddy check did not answer; internal v2.5.0 verification passed."
  fi
fi

echo "=== FINAL CONTAINER ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v2.5.0 deployed and verified on port 8089"
echo "Backup: $backup"
