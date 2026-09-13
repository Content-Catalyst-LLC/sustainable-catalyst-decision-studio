#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="2.6.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v2.6.0.zip}"
ROOT="${SCDS_ROOT:-/opt/sustainable-catalyst/decision-studio}"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
SERVICE="${SCDS_COMPOSE_SERVICE:-decision-studio}"
CONTAINER="${SCDS_CONTAINER:-sc-decision-studio}"
PORT="${SCDS_PORT:-8089}"
PUBLIC_URL="${SCDS_PUBLIC_URL:-https://decision-studio-api.sustainablecatalyst.com}"
BACKUP_ROOT="${SCDS_BACKUP_ROOT:-/opt/sustainable-catalyst/backups}"
TMP="$(mktemp -d /tmp/sc-decision-studio-v260.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

fail(){ echo "ERROR: $*" >&2; exit 1; }
pass(){ echo "PASS: $*"; }

[[ -f "$ARCHIVE" ]] || fail "backend archive not found: $ARCHIVE"
[[ -d "$ROOT" ]] || fail "Decision Studio runtime root not found: $ROOT"
[[ -f "$COMPOSE" ]] || fail "compose file not found: $COMPOSE"
command -v docker >/dev/null 2>&1 || fail "docker is required"
command -v python3 >/dev/null 2>&1 || fail "python3 is required"
command -v unzip >/dev/null 2>&1 || fail "unzip is required"
command -v rsync >/dev/null 2>&1 || fail "rsync is required"
command -v curl >/dev/null 2>&1 || fail "curl is required"

mkdir -p "$BACKUP_ROOT"
unzip -q "$ARCHIVE" -d "$TMP/archive"
SRC="$(find "$TMP/archive" -type f -path '*/backend/app/main.py' -print -quit | sed 's#/app/main.py$##')"
[[ -n "$SRC" ]] || fail "could not locate backend directory in archive"
for required in \
  app/main.py \
  app/native_handoffs.py \
  app/scenario_stress.py \
  app/uncertainty_confidence.py \
  app/tradeoff_matrix.py \
  app/evidence_bundle.py \
  app/decision_object.py \
  app/energy_runtime_consumer.py \
  requirements.txt \
  Dockerfile; do
  [[ -f "$SRC/$required" ]] || fail "v2.6.0 backend payload missing $required"
done
grep -q 'APP_VERSION = "2.6.0"' "$SRC/app/main.py" || fail "payload is not Decision Studio v2.6.0"
grep -q 'scds-v2.6.0-lab-workbench-native-handoffs' "$SRC/app/main.py" || fail "v2.6.0 build fingerprint missing"
grep -q 'CONSUMER_VERSION = .2.3.0.' "$SRC/app/energy_runtime_consumer.py" || fail "preserved Energy Runtime Consumer v2.3.0 missing"

stamp="$(date +%Y%m%d-%H%M%S)"
backup="$BACKUP_ROOT/decision-studio-before-v2.6.0-$stamp.tgz"
echo "=== PRE-FLIGHT ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' || true
curl -fsS "http://127.0.0.1:${PORT}/health" | python3 -m json.tool || true

echo "=== BACKUP ==="
tar -czf "$backup" -C "$ROOT" backend compose.yml
echo "$backup"

mkdir -p "$TMP/env"
for envfile in .env .env.production; do
  [[ -f "$LIVE_BACKEND/$envfile" ]] && cp -a "$LIVE_BACKEND/$envfile" "$TMP/env/$envfile"
done

rsync -a --delete \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='.env.*' \
  "$SRC/" "$LIVE_BACKEND/"
for envfile in .env .env.production; do
  [[ -f "$TMP/env/$envfile" ]] && cp -a "$TMP/env/$envfile" "$LIVE_BACKEND/$envfile"
done

python3 - "$COMPOSE" <<'PY'
from pathlib import Path
import re, sys
p=Path(sys.argv[1]); s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-decision-studio:)[^\s#]+', r'\g<1>2.6.0', s)
s=re.sub(r'(?m)^(\s*SCDS_BUILD_FINGERPRINT:\s*).+$', r'\g<1>scds-v2.6.0-lab-workbench-native-handoffs', s)
s=re.sub(r'(?m)^(\s*SCDS_SOURCE_COMMIT:\s*).+$', r'\g<1>release-v2.6.0', s)
p.write_text(s)
PY

cd "$ROOT"
docker compose config --quiet

echo "=== BUILD v2.6.0 ==="
docker compose build "$SERVICE"
docker compose up -d --force-recreate "$SERVICE"

health=""
for _ in $(seq 1 60); do
  if health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null)"; then
    if python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]); r=x.get('release',{})
assert x.get('ok') is True and x.get('ready') is True
assert x.get('version') == '2.6.0'
assert x.get('build_fingerprint') == 'scds-v2.6.0-lab-workbench-native-handoffs'
assert x.get('source_commit') == 'release-v2.6.0'
assert r.get('analysis_handoff_schema') == 'scds-analysis-handoff/1.0'
assert r.get('computation_handoff_schema') == 'scds-computation-handoff/1.0'
assert r.get('handoff_receipt_schema') == 'scds-handoff-receipt/1.0'
assert r.get('analysis_request_schema') == 'scds-analysis-request/1.0'
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
assert x.get('version') == '2.6.0', x
assert x.get('service') == 'sustainable-catalyst-decision-studio', x
assert x.get('build_fingerprint') == 'scds-v2.6.0-lab-workbench-native-handoffs', x
assert r.get('scenario_set_schema') == 'scds-scenario-set/1.0', r
assert r.get('stress_test_suite_schema') == 'scds-stress-test-suite/1.0', r
assert r.get('analysis_handoff_schema') == 'scds-analysis-handoff/1.0', r
assert r.get('computation_handoff_schema') == 'scds-computation-handoff/1.0', r
assert c.get('lab_native_handoffs') is True, c
assert c.get('workbench_native_handoffs') is True, c
assert c.get('handoff_receipt_implies_validation') is False, c
assert c.get('decision_studio_executes_external_analysis') is False, c
assert c.get('automatic_winner_selection') is False, c
assert c.get('automatic_recommendation') is False, c
assert c.get('energy_systems_runtime_consumer') is True, c
assert c.get('energy_runtime_consumer_version') == '2.3.0', c
print('PASS: internal health identifies Decision Studio backend v2.6.0 with v2.5 Scenario/Stress and Energy v2.3.0 preserved')
PY

echo "=== v2.6.0 NATIVE HANDOFF CONTRACTS ==="
contracts="$(curl -fsS "http://127.0.0.1:${PORT}/native-handoffs/contracts")"
python3 - "$contracts" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); c=x['contracts']
assert x['version']=='2.6.0',x
assert c['analysis_handoff_schema']=='scds-analysis-handoff/1.0',c
assert c['computation_handoff_schema']=='scds-computation-handoff/1.0',c
assert c['handoff_receipt_schema']=='scds-handoff-receipt/1.0',c
assert c['analysis_request_schema']=='scds-analysis-request/1.0',c
assert set(c['products']) == {'research-lab','workbench'},c
print('PASS: Lab + Workbench native handoff contracts are registered')
PY

echo "=== LAB ANALYSIS HANDOFF ==="
lab_payload='{"sourceProduct":"research-lab","sourceVersion":"0.72.0","artifactType":"causal-analysis","artifactSchema":"sc-lab-study-result/1.0","artifact":{"artifact_id":"lab:v260-smoke","schema":"sc-lab-study-result/1.0","artifact_type":"causal-analysis","result":{"effect_estimate":0.18,"interval":[0.05,0.31]},"assumptions":[{"assumption_id":"parallel-trends","status":"reviewed"}],"uncertainty":[{"uncertainty_id":"sampling","type":"statistical"}],"provenance":[{"source":"research-lab","study_id":"v260-smoke"}],"review_state":"reviewed"}}'
lab_receive="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$lab_payload" "http://127.0.0.1:${PORT}/native-handoffs/receive")"
python3 - "$lab_receive" <<'PY'
import hashlib,json,sys
x=json.loads(sys.argv[1]); h=x['handoff']; a=h['artifact']['payload']
raw=json.dumps(a,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
assert x['ok'] is True and x['receipt']['accepted'] is True,x
assert h['schema']=='scds-analysis-handoff/1.0',h
assert h['source']['product']=='research-lab',h
assert h['artifact']['fingerprint']==hashlib.sha256(raw).hexdigest(),h
assert x['receipt']['artifact_fingerprint']==h['artifact']['fingerprint'],x
assert x['receipt']['execution']['performed'] is False,x
print('PASS: Research Lab artifact is accepted with exact deterministic fingerprint and source-owned execution')
PY

echo "=== WORKBENCH COMPUTATION HANDOFF ==="
wb_payload='{"sourceProduct":"workbench","sourceVersion":"5.4.0","artifactType":"engineering-model-output","artifactSchema":"sc-workbench-model-output/1.0","artifact":{"artifact_id":"wb:v260-smoke","schema":"sc-workbench-model-output/1.0","artifact_type":"engineering-model-output","formula":"NPV = -CAPEX + discounted benefits","inputs":{"capex":1000000,"discount_rate":0.05},"results":{"npv":225000,"payback_years":6.4},"assumptions":[{"assumption_id":"discount-rate","value":0.05}],"uncertainty":[{"uncertainty_id":"capex-range","lower":900000,"upper":1200000}],"provenance":[{"source":"workbench","run_id":"v260-smoke"}],"review_state":"reviewed"}}'
wb_receive="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$wb_payload" "http://127.0.0.1:${PORT}/native-handoffs/receive")"
python3 - "$wb_receive" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); h=x['handoff']
assert x['ok'] is True and x['receipt']['accepted'] is True,x
assert h['schema']=='scds-computation-handoff/1.0',h
assert h['source']['product']=='workbench' and h['source']['role']=='computation',h
assert x['receipt']['execution']['performed'] is False,x
print('PASS: Workbench computation artifact is accepted without Decision Studio executing the computation')
PY

echo "=== DECISION STUDIO → WORKBENCH REQUEST + RETURN ==="
request_payload='{"decisionObject":{"schema":"scds-decision-object/1.0","decision_id":"D-V260-SMOKE","provenance":{"records":[]}},"targetProduct":"workbench","question":"Calculate lifecycle cost under the downside scenario.","neededFor":"scenario:downside","request":{"requested_artifact_types":["calculation-report","graph-output"]}}'
request_result="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$request_payload" "http://127.0.0.1:${PORT}/native-handoffs/request")"
python3 - "$request_result" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); r=x['analysis_request']
assert r['schema']=='scds-analysis-request/1.0',r
assert r['target']['product']=='workbench',r
assert r['return_contract']=='scds-computation-handoff/1.0',r
assert r['execution']['performed_by_decision_studio'] is False,r
assert len(r['request_fingerprint'])==64,r
print('PASS: Decision Studio creates a bounded Workbench request without executing it')
PY

return_payload="$(python3 - "$request_result" <<'PY'
import json,sys
x=json.loads(sys.argv[1])
p={
 'decisionObject':x['decision_object'],
 'request':x['analysis_request'],
 'sourceProduct':'workbench','sourceVersion':'5.4.0',
 'artifactType':'calculation-report','artifactSchema':'sc-workbench-model-output/1.0',
 'artifact':{'artifact_id':'wb:v260-return','schema':'sc-workbench-model-output/1.0','artifact_type':'calculation-report','results':{'npv':225000},'assumptions':[],'uncertainty':[],'provenance':[{'source':'workbench','run_id':'v260-return'}],'review_state':'reviewed'}
}
print(json.dumps(p,separators=(',',':')))
PY
)"
return_result="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$return_payload" "http://127.0.0.1:${PORT}/native-handoffs/return")"
python3 - "$return_result" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); h=x['handoff']; r=x['receipt']; o=x['decision_object']
assert x['ok'] is True and r['accepted'] is True,x
assert h['request_id'] and h['request_id']==r['request_id'],x
assert o['computation_handoffs'][-1]['request_id']==h['request_id'],o
assert o['provenance']['records'][-1]['action']=='native_handoff_attached',o
assert o['models'][-1]['source_product']=='workbench',o
print('PASS: returned Workbench artifact attaches to the Unified Decision Object with request lineage intact')
PY

echo "=== TAMPER REJECTION ==="
tampered="$(python3 - "$lab_receive" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); h=x['handoff']; h['artifact']['payload']['result']['effect_estimate']=0.99
print(json.dumps({'handoff':h},separators=(',',':')))
PY
)"
tamper_result="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$tampered" "http://127.0.0.1:${PORT}/native-handoffs/receive")"
python3 - "$tamper_result" <<'PY'
import json,sys
x=json.loads(sys.argv[1])
assert x['ok'] is False,x
assert x['receipt']['accepted'] is False,x
assert any('fingerprint' in e for e in x['validation']['errors']),x
print('PASS: tampered source artifact is rejected by fingerprint validation')
PY

echo "=== DECISION PACKET ATTACHMENT ==="
packet_payload='{"packet":{"decision_packet_id":"P-V260-SMOKE","decision_question":"Which design should proceed?"},"sourceProduct":"workbench","sourceVersion":"5.4.0","artifactType":"calculation-report","artifactSchema":"sc-workbench-model-output/1.0","artifact":{"artifact_id":"wb:packet-smoke","schema":"sc-workbench-model-output/1.0","artifact_type":"calculation-report","results":{"npv":225000},"provenance":[{"source":"workbench"}]}}'
packet_result="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$packet_payload" "http://127.0.0.1:${PORT}/decision-packet/native-handoff")"
python3 - "$packet_result" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x['decision_packet']
assert x['ok'] is True,x
assert p['native_handoffs'][-1]['schema']=='scds-computation-handoff/1.0',p
assert p['handoff_receipts'][-1]['schema']=='scds-handoff-receipt/1.0',p
assert p['decision_object']['schema']=='scds-decision-object/1.0',p
print('PASS: native Workbench handoff projects into Decision Packet without breaking its schema')
PY

echo "=== PRESERVED v2.5.0 SCENARIO / STRESS ROUTES ==="
scenario_template="$(curl -fsS "http://127.0.0.1:${PORT}/scenario-set/template")"
stress_template="$(curl -fsS "http://127.0.0.1:${PORT}/stress-test-suite/template")"
python3 - "$scenario_template" "$stress_template" <<'PY'
import json,sys
s=json.loads(sys.argv[1]); t=json.loads(sys.argv[2])
assert s['scenario_set']['schema']=='scds-scenario-set/1.0',s
assert t['stress_test_suite']['schema']=='scds-stress-test-suite/1.0',t
print('PASS: v2.5 Scenario Comparison / Stress Testing contracts remain live')
PY

echo "=== PRESERVED v2.3.0 ENERGY RUNTIME CONSUMER ==="
energy_framework="$(curl -fsS "http://127.0.0.1:${PORT}/v1/energy-runtime/consumer")"
python3 - "$energy_framework" <<'PY'
import json,sys
x=json.loads(sys.argv[1])
assert x.get('ok') is True,x
assert x.get('consumer_version')=='2.3.0',x
assert x.get('consumer_contract')=='sc-energy-runtime-decision-studio-handoff/1.0',x
assert x.get('capabilities',{}).get('automatic_ranking') is False,x
assert x.get('capabilities',{}).get('automatic_recommendation') is False,x
print('PASS: Energy Systems Runtime Consumer v2.3.0 remains registered')
PY
energy_payload='{"schema":"sc-energy-runtime-handoff/1.0","version":"1.2.0","packet":{"handoff_id":"es-v260-smoke","source":{"product":"Library","subsystem":"Energy Systems Intelligence","version":"1.2.0"},"target":{"key":"decision-studio","product":"Decision Studio","consumer_contract":"sc-energy-runtime-decision-studio-handoff/1.0"},"contract_refs":["integrated-energy-study-contract"],"payload":{"identity":{"study_id":"study:v260-smoke","question":"Compare energy pathways"},"decision":{},"economics":{},"sustainability_indicators":[],"global_context":{},"uncertainty":[],"provenance":[{"source_ref":"source:v260-smoke"}],"review":{}}}}'
energy_receipt="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$energy_payload" "http://127.0.0.1:${PORT}/v1/energy-runtime/consume")"
python3 - "$energy_receipt" <<'PY'
import json,sys
x=json.loads(sys.argv[1])
assert x.get('accepted') is True,x
assert x.get('consumer',{}).get('app_version')=='2.3.0',x
assert x.get('execution',{}).get('performed') is False,x
assert x.get('persistence',{}).get('performed') is False,x
print('PASS: Energy Systems handoff acceptance remains compatible and bounded')
PY

if [[ -n "$PUBLIC_URL" ]]; then
  echo "=== PUBLIC CADDY CHECK ==="
  if public_health="$(curl -fsS --max-time 20 "${PUBLIC_URL%/}/health" 2>/dev/null)"; then
    python3 - "$public_health" <<'PY'
import json,sys
x=json.loads(sys.argv[1])
assert x.get('ok') is True and x.get('ready') is True,x
assert x.get('version')=='2.6.0',x
assert x.get('build_fingerprint')=='scds-v2.6.0-lab-workbench-native-handoffs',x
print('PASS: public Decision Studio API returns v2.6.0')
PY
  else
    echo "WARNING: public Caddy check did not answer; internal v2.6.0 verification passed."
  fi
fi

echo "=== FINAL CONTAINER ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v2.6.0 deployed and verified on port 8089"
echo "Backup: $backup"
