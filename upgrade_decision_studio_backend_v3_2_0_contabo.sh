#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="3.2.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v3.2.0.zip}"
ROOT="${SCDS_ROOT:-/opt/sustainable-catalyst/decision-studio}"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
SERVICE="${SCDS_COMPOSE_SERVICE:-decision-studio}"
CONTAINER="${SCDS_CONTAINER:-sc-decision-studio}"
PORT="${SCDS_PORT:-8089}"
PUBLIC_URL="${SCDS_PUBLIC_URL:-https://decision-studio-api.sustainablecatalyst.com}"
BACKUP_ROOT="${SCDS_BACKUP_ROOT:-/opt/sustainable-catalyst/backups}"
TMP="$(mktemp -d /tmp/sc-decision-studio-v320.XXXXXX)"
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
for required in app/main.py app/api/router.py app/services/decision_service.py app/decision_kernel.py app/connected_decision_intelligence.py app/recommendation_review.py app/dependency_graph.py app/site_intelligence_context.py app/native_handoffs.py app/scenario_stress.py app/energy_runtime_consumer.py requirements.txt Dockerfile; do [[ -f "$SRC/$required" ]] || fail "v3.2.0 backend payload missing $required"; done
grep -q 'APP_VERSION = "3.2.0"' "$SRC/app/services/decision_service.py" || fail "payload is not Decision Studio v3.2.0"
grep -q 'scds-v3.2.0-decision-kernel-module-contract-foundation' "$SRC/app/services/decision_service.py" || fail "v3.2.0 build fingerprint missing"
grep -q 'DECISION_KERNEL_SCHEMA = "scds-decision-kernel/1.0"' "$SRC/app/decision_kernel.py" || fail "Decision Kernel contract missing"
grep -q '"finance"' "$SRC/app/decision_kernel.py" || fail "Finance module contract missing"
grep -q '"narrative-risk"' "$SRC/app/decision_kernel.py" || fail "Narrative Risk module contract missing"
grep -q '"global-impact"' "$SRC/app/decision_kernel.py" || fail "Global Impact module contract missing"
grep -q 'include_router(api_router)' "$SRC/app/main.py" || fail "composition-only main missing API router"

echo "=== PRE-FLIGHT ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' || true
curl -fsS "http://127.0.0.1:${PORT}/health" | python3 -m json.tool || true
stamp="$(date +%Y%m%d-%H%M%S)"; backup="$BACKUP_ROOT/decision-studio-before-v3.2.0-$stamp.tgz"
echo "=== BACKUP ==="; tar -czf "$backup" -C "$ROOT" backend compose.yml; echo "$backup"
mkdir -p "$TMP/env"; for envfile in .env .env.production; do [[ -f "$LIVE_BACKEND/$envfile" ]] && cp -a "$LIVE_BACKEND/$envfile" "$TMP/env/$envfile"; done
rsync -a --delete --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='*.pyc' --exclude='.env' --exclude='.env.*' "$SRC/" "$LIVE_BACKEND/"
for envfile in .env .env.production; do [[ -f "$TMP/env/$envfile" ]] && cp -a "$TMP/env/$envfile" "$LIVE_BACKEND/$envfile"; done
python3 - "$COMPOSE" <<'PY2'
from pathlib import Path
import re,sys
p=Path(sys.argv[1]);s=p.read_text()
s=re.sub(r'(?m)^(\s*image:\s*sustainable-catalyst-decision-studio:)[^\s#]+',r'\g<1>3.2.0',s)
s=re.sub(r'(?m)^(\s*SCDS_BUILD_FINGERPRINT:\s*).+$',r'\g<1>scds-v3.2.0-decision-kernel-module-contract-foundation',s)
s=re.sub(r'(?m)^(\s*SCDS_SOURCE_COMMIT:\s*).+$',r'\g<1>release-v3.2.0',s)
p.write_text(s)
PY2
cd "$ROOT"; docker compose config --quiet
echo "=== BUILD v3.2.0 ==="; docker compose build "$SERVICE"; docker compose up -d --force-recreate "$SERVICE"
health=""
for _ in $(seq 1 60); do
  if health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null)"; then
    if python3 - "$health" <<'PY2' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]);r=x.get('release',{});k=r.get('decision_kernel',{})
assert x.get('ok') is True and x.get('ready') is True
assert x.get('version')=='3.2.0'
assert x.get('build_fingerprint')=='scds-v3.2.0-decision-kernel-module-contract-foundation'
assert x.get('source_commit')=='release-v3.2.0'
assert x.get('decision_kernel_schema')=='scds-decision-kernel/1.0'
assert x.get('registered_decision_modules')==4
assert k.get('module_count')==4 and k.get('final_decision_authority')=='human-governed'
assert r.get('backend_architecture',{}).get('database_migration') is False
assert r.get('backend_architecture',{}).get('wordpress_authority_change') is False
PY2
    then break; fi
  fi
  sleep 2
done
[[ -n "$health" ]] || { docker logs --tail=200 "$CONTAINER" >&2 || true; fail "backend did not answer /health"; }
python3 - "$health" <<'PY2'
import json,sys
x=json.loads(sys.argv[1]);r=x['release'];k=r['decision_kernel'];a=r['backend_architecture']
assert x['version']=='3.2.0' and x['registered_decision_modules']==4,x
assert k['module_ids']==['canvas','finance','global-impact','narrative-risk'] or set(k['module_ids'])=={'canvas','finance','global-impact','narrative-risk'},k
assert k['final_decision_authority']=='human-governed',k
assert a['route_count']==182 and a['router_registry_count']==12,a
assert a['database_migration'] is False and a['wordpress_authority_change'] is False,a
print('PASS: internal v3.2.0 health identifies Decision Kernel + four module contracts with migration boundaries preserved')
PY2

echo "=== MODULE REGISTRY SMOKE ==="
mods="$(curl -fsS "http://127.0.0.1:${PORT}/decision-modules")"
python3 - "$mods" <<'PY2'
import json,sys
x=json.loads(sys.argv[1]);r=x['registry'];ids={m['module_id'] for m in r['modules']}
assert r['module_count']==4 and ids=={'canvas','finance','narrative-risk','global-impact'},r
finance=next(m for m in r['modules'] if m['module_id']=='finance')
assert finance['providers']['compute_authority']=='workbench',finance
print('PASS: Canvas, Finance, Narrative Risk, and Global Impact Catalyst are registered; Finance compute authority is Workbench')
PY2

echo "=== KERNEL VALIDATION SMOKE ==="
validated="$(curl -fsS -H 'Content-Type: application/json' -X POST -d '{"kernel":{"schema":"scds-decision-kernel/1.0","decision":{"decision_id":"deploy-smoke","decision_question":"Which governed option should advance?"},"module_bindings":[{"module_id":"canvas"},{"module_id":"finance"}],"authorities":{"final_decision_authority":"human-governed"}}}' "http://127.0.0.1:${PORT}/decision-kernel/validate")"
python3 - "$validated" <<'PY2'
import json,sys
x=json.loads(sys.argv[1]);assert x['ok'] is True,x
assert x['module_ids']==['canvas','finance'],x
assert x['normalized_kernel']['authorities']['final_decision_authority']=='human-governed',x
print('PASS: Decision Kernel validation is live')
PY2

echo "=== PRESERVED v3.1/v3.0 LAYERS ==="
python3 - "$PORT" <<'PY2'
import json,sys,urllib.request
p=sys.argv[1]
def get(path): return json.load(urllib.request.urlopen(f'http://127.0.0.1:{p}{path}',timeout=5))
assert get('/connected-intelligence/template')['connected_intelligence']['schema']=='scds-connected-decision-intelligence/3.0'
assert get('/recommendation-review/template')['recommendation_candidate']['schema']=='scds-recommendation-candidate/1.0'
assert get('/decision-dependency-graph/template')['dependency_graph']['schema']=='scds-decision-dependency-graph/1.0'
assert get('/site-intelligence-context/template')['context_bundle']['schema']=='scds-site-intelligence-context-bundle/1.0'
assert get('/native-handoffs/contracts')['contracts']['analysis_handoff_schema']=='scds-analysis-handoff/1.0'
assert get('/v1/energy-runtime/consumer')['consumer_version']=='2.3.0'
print('PASS: connected intelligence and specialized pre-v3.2 domains remain live')
PY2

echo "=== PUBLIC CADDY CHECK ==="
public="$(curl -fsS "$PUBLIC_URL/health")"
python3 - "$public" <<'PY2'
import json,sys
x=json.loads(sys.argv[1]);assert x['version']=='3.2.0' and x['build_fingerprint']=='scds-v3.2.0-decision-kernel-module-contract-foundation',x
assert x['registered_decision_modules']==4,x
print('PASS: public Decision Studio API returns v3.2.0')
PY2
curl -fsS "$PUBLIC_URL/decision-modules" | python3 -m json.tool

echo "=== FINAL CONTAINER ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v3.2.0 deployed and verified on port $PORT"
echo "Backup: $backup"
