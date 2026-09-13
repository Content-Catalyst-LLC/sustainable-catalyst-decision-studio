#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="2.9.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v2.9.0.zip}"
ROOT="${SCDS_ROOT:-/opt/sustainable-catalyst/decision-studio}"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
SERVICE="${SCDS_COMPOSE_SERVICE:-decision-studio}"
CONTAINER="${SCDS_CONTAINER:-sc-decision-studio}"
PORT="${SCDS_PORT:-8089}"
PUBLIC_URL="${SCDS_PUBLIC_URL:-https://decision-studio-api.sustainablecatalyst.com}"
BACKUP_ROOT="${SCDS_BACKUP_ROOT:-/opt/sustainable-catalyst/backups}"
TMP="$(mktemp -d /tmp/sc-decision-studio-v290.XXXXXX)"
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
for required in app/main.py app/recommendation_review.py app/dependency_graph.py app/site_intelligence_context.py app/native_handoffs.py app/scenario_stress.py app/energy_runtime_consumer.py requirements.txt Dockerfile; do [[ -f "$SRC/$required" ]] || fail "v2.9.0 backend payload missing $required"; done
grep -q 'APP_VERSION = "2.9.0"' "$SRC/app/main.py" || fail "payload is not Decision Studio v2.9.0"
grep -q 'scds-v2.9.0-recommendations-review-challenge' "$SRC/app/main.py" || fail "v2.9.0 build fingerprint missing"
grep -q 'CONSUMER_VERSION = .2.3.0.' "$SRC/app/energy_runtime_consumer.py" || fail "Energy Runtime Consumer v2.3.0 missing"

echo "=== PRE-FLIGHT ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' || true
curl -fsS "http://127.0.0.1:${PORT}/health" | python3 -m json.tool || true
stamp="$(date +%Y%m%d-%H%M%S)"; backup="$BACKUP_ROOT/decision-studio-before-v2.9.0-$stamp.tgz"
echo "=== BACKUP ==="; tar -czf "$backup" -C "$ROOT" backend compose.yml; echo "$backup"
mkdir -p "$TMP/env"; for envfile in .env .env.production; do [[ -f "$LIVE_BACKEND/$envfile" ]] && cp -a "$LIVE_BACKEND/$envfile" "$TMP/env/$envfile"; done
rsync -a --delete --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='*.pyc' --exclude='.env' --exclude='.env.*' "$SRC/" "$LIVE_BACKEND/"
for envfile in .env .env.production; do [[ -f "$TMP/env/$envfile" ]] && cp -a "$TMP/env/$envfile" "$LIVE_BACKEND/$envfile"; done
python3 - "$COMPOSE" <<'PY'
from pathlib import Path
import re,sys
p=Path(sys.argv[1]);s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-decision-studio:)[^\s#]+',r'\g<1>2.9.0',s)
s=re.sub(r'(?m)^(\s*SCDS_BUILD_FINGERPRINT:\s*).+$',r'\g<1>scds-v2.9.0-recommendations-review-challenge',s)
s=re.sub(r'(?m)^(\s*SCDS_SOURCE_COMMIT:\s*).+$',r'\g<1>release-v2.9.0',s)
p.write_text(s)
PY
cd "$ROOT"; docker compose config --quiet
echo "=== BUILD v2.9.0 ==="; docker compose build "$SERVICE"; docker compose up -d --force-recreate "$SERVICE"
health=""; for _ in $(seq 1 60); do if health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null)"; then if python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]);r=x.get('release',{})
assert x.get('ok') is True and x.get('ready') is True
assert x.get('version')=='2.9.0'
assert x.get('build_fingerprint')=='scds-v2.9.0-recommendations-review-challenge'
assert x.get('source_commit')=='release-v2.9.0'
assert r.get('recommendation_candidate_schema')=='scds-recommendation-candidate/1.0'
assert r.get('recommendation_challenge_schema')=='scds-recommendation-challenge/1.0'
assert r.get('recommendation_review_schema')=='scds-recommendation-review/1.0'
PY
then break; fi; fi; sleep 2; done
[[ -n "$health" ]] || { docker logs --tail=200 "$CONTAINER" >&2 || true; fail "backend did not answer /health"; }
python3 - "$health" <<'PY'
import json,sys
x=json.loads(sys.argv[1]);r=x['release'];c=r['compatibility']
assert x['version']=='2.9.0' and x['build_fingerprint']=='scds-v2.9.0-recommendations-review-challenge',x
assert c['recommendation_candidates'] is True and c['recommendation_challenges'] is True and c['human_recommendation_disposition'] is True,c
assert c['recommendation_candidate_implies_winner'] is False and c['recommendation_score_implies_approval'] is False,c
assert c['challenge_resolution_is_automatic'] is False and c['human_disposition_executes_decision'] is False,c
assert c['v2_8_0_dependency_graph_preserved'] is True and c['decision_dependency_graphs'] is True,c
assert c['v2_7_0_site_intelligence_context_preserved'] is True,c
assert c['lab_native_handoffs'] is True and c['workbench_native_handoffs'] is True,c
assert c['energy_runtime_consumer_version']=='2.3.0',c
print('PASS: internal health identifies Decision Studio backend v2.9.0 and preserves v2.8→v2.3 compatibility')
PY

echo "=== v2.9.0 RECOMMENDATION CANDIDATE ==="
graph_payload='{"decisionObject":{"schema":"scds-decision-object/1.0","decision_id":"D-V290-SMOKE","question":"Which option should proceed to human decision?","evidence":[{"evidence_id":"ev1","label":"Reviewed evidence"}],"assumptions":[{"assumption_id":"a1","label":"Demand assumption"}],"models":[{"model_id":"m1","label":"Cost model","evidence_refs":["ev1"]}],"scenarios":[{"scenario_id":"s1","label":"Stress"}],"criteria":[{"criterion_id":"c1","label":"Cost"}],"alternatives":[{"alternative_id":"alt-a","label":"Option A"},{"alternative_id":"alt-b","label":"Option B"}],"uncertainties":[{"uncertainty_id":"u1","label":"Demand uncertainty"}],"recommendation":{"summary":"Legacy recommendation remains untouched."},"provenance":{"records":[]}}}'
graph_build="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$graph_payload" "http://127.0.0.1:${PORT}/decision-dependency-graph/build")"
candidate_payload="$(python3 - "$graph_build" <<'PY'
import json,sys
x=json.loads(sys.argv[1]);g=x['dependency_graph']
ev=next(n['node_id'] for n in g['nodes'] if n['node_type']=='evidence')
u=next(n['node_id'] for n in g['nodes'] if n['node_type']=='uncertainty')
obj={'schema':'scds-decision-object/1.0','decision_id':'D-V290-SMOKE','alternatives':[{'alternative_id':'alt-a','label':'Option A'},{'alternative_id':'alt-b','label':'Option B'}],'recommendation':{'summary':'Legacy recommendation remains untouched.'},'provenance':{'records':[]}}
print(json.dumps({'decisionObject':obj,'graph':g,'selectedAlternativeId':'alt-a','rationale':['Advance Option A for human review.'],'supportNodeIds':[ev],'counterNodeIds':[u],'conditions':['Recheck demand before commitment.']},separators=(',',':')))
PY
)"
candidate_result="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$candidate_payload" "http://127.0.0.1:${PORT}/recommendation-review/candidate")"
python3 - "$candidate_result" <<'PY'
import json,sys
x=json.loads(sys.argv[1]);c=x['candidate']
assert x['ok'] is True and c['selected_alternative_id']=='alt-a',x
assert c['automatic_selection'] is False and c['automatic_approval'] is False,c
assert c['explicit_support_node_ids'] and c['explicit_counter_node_ids'],c
assert len(c['candidate_fingerprint'])==64,c
print('PASS: explicit human-selected recommendation candidate preserves support/counterargument links without winner selection')
PY

echo "=== CHALLENGE + REVIEW GATE ==="
challenge_payload="$(python3 - "$candidate_result" "$graph_build" <<'PY'
import json,sys
c=json.loads(sys.argv[1])['candidate'];g=json.loads(sys.argv[2])['dependency_graph']
print(json.dumps({'candidate':c,'graph':g,'challengeAction':'create','challengeType':'assumption_dispute','statement':'Demand assumption remains contested under stress.','actor':'reviewer-smoke'},separators=(',',':')))
PY
)"
challenge_result="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$challenge_payload" "http://127.0.0.1:${PORT}/recommendation-review/challenge")"
python3 - "$challenge_result" <<'PY'
import json,sys
x=json.loads(sys.argv[1]);r=x['review'];ch=x['challenge']
assert ch['status']=='open' and ch['automatic_disposition'] is False,ch
assert r['review_status']=='blocked_by_open_challenges' and r['decision_ready'] is False,r
assert r['automatic_approval'] is False and r['automatic_recommendation'] is False,r
print('PASS: open reviewer challenge blocks accepting review state without automatic rejection or approval')
PY

echo "=== HUMAN DISPOSITION OVERRIDE ==="
disposition_payload="$(python3 - "$challenge_result" "$graph_build" <<'PY'
import json,sys
x=json.loads(sys.argv[1]);g=json.loads(sys.argv[2])['dependency_graph']
print(json.dumps({'candidate':x['candidate'],'challenges':x['challenges'],'review':x['review'],'graph':g,'disposition':'accept_for_decision','actor':'human-owner','dispositionRationale':'Advance to human decision with the unresolved challenge explicitly acknowledged.','overrideOpenChallenges':True},separators=(',',':')))
PY
)"
disposition_result="$(curl -fsS -H 'Content-Type: application/json' -X POST -d "$disposition_payload" "http://127.0.0.1:${PORT}/recommendation-review/disposition")"
python3 - "$disposition_result" <<'PY'
import json,sys
x=json.loads(sys.argv[1]);d=x['review']['human_disposition']
assert x['ok'] is True and x['review']['decision_ready'] is True,x
assert d['override_open_challenges'] is True,d
assert d['execution_authorized'] is False and d['approval_inferred'] is False,d
print('PASS: human disposition is explicit, auditable, and non-executing')
PY

echo "=== CANDIDATE TAMPER REJECTION ==="
tampered="$(python3 - "$candidate_result" "$graph_build" <<'PY'
import json,sys
c=json.loads(sys.argv[1])['candidate'];c['selected_alternative_id']='alt-b';g=json.loads(sys.argv[2])['dependency_graph']
print(json.dumps({'candidate':c,'graph':g},separators=(',',':')))
PY
)"
status="$(curl -sS -o "$TMP/tamper.json" -w '%{http_code}' -H 'Content-Type: application/json' -X POST -d "$tampered" "http://127.0.0.1:${PORT}/recommendation-review/evaluate")"
[[ "$status" == "400" ]] || fail "tampered candidate expected HTTP 400; got $status"
python3 - "$TMP/tamper.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]));assert any('fingerprint' in e for e in x['validation']['errors']),x
print('PASS: tampered recommendation candidate is rejected by fingerprint validation')
PY

echo "=== PRESERVED RELEASE LAYERS ==="
python3 - "$PORT" <<'PY'
import json,sys,urllib.request
p=sys.argv[1]
def get(path): return json.load(urllib.request.urlopen(f'http://127.0.0.1:{p}{path}',timeout=5))
assert get('/decision-dependency-graph/template')['dependency_graph']['schema']=='scds-decision-dependency-graph/1.0'
assert get('/site-intelligence-context/template')['context_bundle']['schema']=='scds-site-intelligence-context-bundle/1.0'
assert get('/native-handoffs/contracts')['contracts']['analysis_handoff_schema']=='scds-analysis-handoff/1.0'
assert get('/scenario-set/template')['scenario_set']['schema']=='scds-scenario-set/1.0'
assert get('/stress-test-suite/template')['stress_test_suite']['schema']=='scds-stress-test-suite/1.0'
assert get('/v1/energy-runtime/consumer')['consumer_version']=='2.3.0'
print('PASS: v2.8 graph, v2.7 context, v2.6 handoffs, v2.5 scenario/stress, and Energy v2.3.0 remain live')
PY

echo "=== PUBLIC CADDY CHECK ==="
public="$(curl -fsS "$PUBLIC_URL/health")"
python3 - "$public" <<'PY'
import json,sys
x=json.loads(sys.argv[1]);assert x['version']=='2.9.0' and x['build_fingerprint']=='scds-v2.9.0-recommendations-review-challenge',x
print('PASS: public Decision Studio API returns v2.9.0')
PY

echo "=== FINAL CONTAINER ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v2.9.0 deployed and verified on port $PORT"
echo "Backup: $backup"
