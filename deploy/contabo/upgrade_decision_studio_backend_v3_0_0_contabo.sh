#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="3.0.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v3.0.0.zip}"
ROOT="${SCDS_ROOT:-/opt/sustainable-catalyst/decision-studio}"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
SERVICE="${SCDS_COMPOSE_SERVICE:-decision-studio}"
CONTAINER="${SCDS_CONTAINER:-sc-decision-studio}"
PORT="${SCDS_PORT:-8089}"
PUBLIC_URL="${SCDS_PUBLIC_URL:-https://decision-studio-api.sustainablecatalyst.com}"
BACKUP_ROOT="${SCDS_BACKUP_ROOT:-/opt/sustainable-catalyst/backups}"
TMP="$(mktemp -d /tmp/sc-decision-studio-v300.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }
pass(){ echo "PASS: $*"; }
[[ -f "$ARCHIVE" ]] || fail "backend archive not found: $ARCHIVE"
[[ -d "$ROOT" && -f "$COMPOSE" ]] || fail "Decision Studio runtime root/compose missing: $ROOT"
for c in docker python3 unzip rsync curl; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
mkdir -p "$BACKUP_ROOT"
unzip -q "$ARCHIVE" -d "$TMP/archive"
SRC="$(find "$TMP/archive" -type f -path '*/backend/app/main.py' -print -quit | sed 's#/app/main.py$##')"
[[ -n "$SRC" ]] || fail "could not locate backend directory in archive"
for required in app/main.py app/connected_decision_intelligence.py app/recommendation_review.py app/dependency_graph.py app/site_intelligence_context.py app/native_handoffs.py app/scenario_stress.py app/energy_runtime_consumer.py requirements.txt Dockerfile; do [[ -f "$SRC/$required" ]] || fail "v3.0.0 backend payload missing $required"; done
grep -q 'APP_VERSION = "3.0.0"' "$SRC/app/main.py" || fail "payload is not Decision Studio v3.0.0"
grep -q 'scds-v3.0.0-connected-decision-intelligence' "$SRC/app/main.py" || fail "v3.0.0 build fingerprint missing"
grep -q 'scds-connected-decision-intelligence/3.0' "$SRC/app/connected_decision_intelligence.py" || fail "Connected Decision Intelligence contract missing"
grep -q 'CONSUMER_VERSION = .2.3.0.' "$SRC/app/energy_runtime_consumer.py" || fail "Energy Runtime Consumer v2.3.0 missing"

echo "=== PRE-FLIGHT ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' || true
curl -fsS "http://127.0.0.1:${PORT}/health" | python3 -m json.tool || true
stamp="$(date +%Y%m%d-%H%M%S)"; backup="$BACKUP_ROOT/decision-studio-before-v3.0.0-$stamp.tgz"
echo "=== BACKUP ==="; tar -czf "$backup" -C "$ROOT" backend compose.yml; echo "$backup"
mkdir -p "$TMP/env"; for envfile in .env .env.production; do [[ -f "$LIVE_BACKEND/$envfile" ]] && cp -a "$LIVE_BACKEND/$envfile" "$TMP/env/$envfile"; done
rsync -a --delete --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='*.pyc' --exclude='.env' --exclude='.env.*' "$SRC/" "$LIVE_BACKEND/"
for envfile in .env .env.production; do [[ -f "$TMP/env/$envfile" ]] && cp -a "$TMP/env/$envfile" "$LIVE_BACKEND/$envfile"; done
python3 - "$COMPOSE" <<'PY'
from pathlib import Path
import re,sys
p=Path(sys.argv[1]);s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-decision-studio:)[^\s#]+',r'\g<1>3.0.0',s)
s=re.sub(r'(?m)^(\s*SCDS_BUILD_FINGERPRINT:\s*).+$',r'\g<1>scds-v3.0.0-connected-decision-intelligence',s)
s=re.sub(r'(?m)^(\s*SCDS_SOURCE_COMMIT:\s*).+$',r'\g<1>release-v3.0.0',s)
p.write_text(s)
PY
cd "$ROOT"; docker compose config --quiet
echo "=== BUILD v3.0.0 ==="; docker compose build "$SERVICE"; docker compose up -d --force-recreate "$SERVICE"
health=""
for _ in $(seq 1 60); do
  if health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null)"; then
    if python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]);r=x.get('release',{})
assert x.get('ok') is True and x.get('ready') is True
assert x.get('version')=='3.0.0'
assert x.get('build_fingerprint')=='scds-v3.0.0-connected-decision-intelligence'
assert x.get('source_commit')=='release-v3.0.0'
assert r.get('connected_decision_intelligence_schema')=='scds-connected-decision-intelligence/3.0'
assert r.get('decision_lifecycle_state_schema')=='scds-decision-lifecycle-state/1.0'
assert r.get('decision_readiness_matrix_schema')=='scds-decision-readiness-matrix/1.0'
assert r.get('cross_product_route_plan_schema')=='scds-cross-product-route-plan/1.0'
PY
    then break; fi
  fi
  sleep 2
done
[[ -n "$health" ]] || { docker logs --tail=200 "$CONTAINER" >&2 || true; fail "backend did not answer /health"; }
python3 - "$health" <<'PY'
import json,sys
x=json.loads(sys.argv[1]);c=x['release']['compatibility']
assert x['version']=='3.0.0' and x['build_fingerprint']=='scds-v3.0.0-connected-decision-intelligence',x
assert c['connected_decision_intelligence_v3'] is True and c['canonical_eight_stage_lifecycle'] is True,c
assert c['cross_product_readiness_matrix'] is True and c['bounded_cross_product_route_plan'] is True,c
assert c['readiness_implies_approval'] is False and c['lifecycle_stage_transition_is_automatic'] is False,c
assert c['route_plan_executes_external_work'] is False and c['decision_record_is_human_owned'] is True,c
assert c['v2_9_0_recommendation_review_preserved'] is True,c
assert c['energy_runtime_consumer_version']=='2.3.0',c
print('PASS: internal health identifies Decision Studio v3.0.0 with human-controlled connected intelligence boundaries')
PY

echo "=== v3.0.0 EIGHT-STAGE CONNECTED INTELLIGENCE ==="
cat > "$TMP/request.json" <<'JSON'
{"decisionObject":{"schema":"scds-decision-object/1.0","version":"3.0.0","decision_id":"D-V300-SMOKE","question":"Which bounded option should proceed to human decision?","objective":"Verify connected lifecycle orchestration.","evidence":[{"evidence_id":"ev1"}],"models":[{"model_id":"m1"}],"alternatives":[{"alternative_id":"alt-a"},{"alternative_id":"alt-b"}],"criteria":[{"criterion_id":"c1"}],"tradeoff_matrices":[{"schema":"scds-tradeoff-matrix/1.0"}],"sensitivity_analyses":[{"schema":"scds-sensitivity-analysis/1.0"}],"dependency_graphs":[{"schema":"scds-decision-dependency-graph/1.0"}],"recommendation_candidates":[{"schema":"scds-recommendation-candidate/1.0"}],"recommendation_reviews":[{"schema":"scds-recommendation-review/1.0","human_disposition":{"disposition":"accept_for_decision","actor":"human-reviewer"},"decision_ready":true}],"platform_context":{"artifact_links":[{"product":"knowledge-library","artifact_id":"bundle:1"}]},"provenance":{"records":[]}}}
JSON
connected="$(curl -fsS -H 'Content-Type: application/json' -X POST --data-binary @"$TMP/request.json" "http://127.0.0.1:${PORT}/connected-intelligence/build")"
python3 - "$connected" <<'PY'
import json,sys
x=json.loads(sys.argv[1]);ci=x['connected_intelligence']; rows=ci['readiness_matrix']['stages']; lc=ci['lifecycle_state']; rp=ci['route_plan']
assert x['ok'] is True and len(rows)==8,x
assert [r['stage_id'] for r in rows]==['frame','evidence','analyze','compare','stress','review','decide','monitor'],rows
assert lc['current_stage']=='decide' and lc['automatic_transition'] is False and lc['human_transition_required'] is True,lc
assert rp['external_execution_performed'] is False and all(r['execution_performed'] is False for r in rp['routes']),rp
assert all(v is False for v in ci['human_control'].values()),ci['human_control']
assert any(r['product']=='decision-studio' and r['stage_id']=='decide' for r in rp['routes']),rp
assert any(x.get('product')=='knowledge-library' for x in ci['cross_product_lineage']),ci['cross_product_lineage']
print('PASS: eight-stage lifecycle, readiness, lineage, and bounded next-action routes are live without automatic progression')
PY

echo "=== CONNECTED INTELLIGENCE TAMPER REJECTION ==="
tampered="$(python3 - "$connected" <<'PY'
import json,sys
x=json.loads(sys.argv[1]);ci=x['connected_intelligence'];ci['decision_id']='tampered';print(json.dumps({'connectedIntelligence':ci},separators=(',',':')))
PY
)"
tamper_result="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$tampered" "http://127.0.0.1:${PORT}/connected-intelligence/validate")"
python3 - "$tamper_result" <<'PY'
import json,sys
x=json.loads(sys.argv[1]);assert x['ok'] is False and x['validation']['valid'] is False,x
assert any('fingerprint' in e for e in x['validation']['errors']),x
print('PASS: modified connected-intelligence payload is rejected by deterministic fingerprint validation')
PY

echo "=== DECISION PACKET ATTACHMENT ==="
attach_payload="$(python3 - "$connected" "$TMP/request.json" <<'PY'
import json,sys
ci=json.loads(sys.argv[1])['connected_intelligence']; req=json.load(open(sys.argv[2])); req['connectedIntelligence']=ci;print(json.dumps(req,separators=(',',':')))
PY
)"
attached="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$attach_payload" "http://127.0.0.1:${PORT}/decision-packet/connected-intelligence")"
python3 - "$attached" <<'PY'
import json,sys
x=json.loads(sys.argv[1]);p=x['decision_packet'];o=x['decision_object']
assert x['ok'] is True and p['connected_intelligence']['schema']=='scds-connected-decision-intelligence/3.0',x
assert p['decision_lifecycle_state']['schema']=='scds-decision-lifecycle-state/1.0',p
assert p['decision_readiness_matrix']['schema']=='scds-decision-readiness-matrix/1.0',p
assert p['cross_product_route_plan']['schema']=='scds-cross-product-route-plan/1.0',p
assert any(r.get('action')=='connected_decision_intelligence_attached' for r in o['provenance']['records']),o
print('PASS: Connected Decision Intelligence attaches to Decision Object and Decision Packet with lineage intact')
PY

echo "=== PRESERVED RELEASE LAYERS ==="
python3 - "$PORT" <<'PY'
import json,sys,urllib.request
p=sys.argv[1]
def get(path): return json.load(urllib.request.urlopen(f'http://127.0.0.1:{p}{path}',timeout=5))
assert get('/recommendation-review/template')['recommendation_candidate']['schema']=='scds-recommendation-candidate/1.0'
assert get('/decision-dependency-graph/template')['dependency_graph']['schema']=='scds-decision-dependency-graph/1.0'
assert get('/site-intelligence-context/template')['context_bundle']['schema']=='scds-site-intelligence-context-bundle/1.0'
assert get('/native-handoffs/contracts')['contracts']['analysis_handoff_schema']=='scds-analysis-handoff/1.0'
assert get('/scenario-set/template')['scenario_set']['schema']=='scds-scenario-set/1.0'
assert get('/stress-test-suite/template')['stress_test_suite']['schema']=='scds-stress-test-suite/1.0'
assert get('/v1/energy-runtime/consumer')['consumer_version']=='2.3.0'
print('PASS: v2.9 review, v2.8 graph, v2.7 context, v2.6 handoffs, v2.5 scenario/stress, and Energy v2.3.0 remain live')
PY

echo "=== PUBLIC CADDY CHECK ==="
public="$(curl -fsS "$PUBLIC_URL/health")"
python3 - "$public" <<'PY'
import json,sys
x=json.loads(sys.argv[1]);assert x['version']=='3.0.0' and x['build_fingerprint']=='scds-v3.0.0-connected-decision-intelligence',x
print('PASS: public Decision Studio API returns v3.0.0')
PY

echo "=== FINAL CONTAINER ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v3.0.0 deployed and verified on port $PORT"
echo "Backup: $backup"
