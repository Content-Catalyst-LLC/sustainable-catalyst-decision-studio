#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="3.10.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v3.10.0.zip}"
ROOT="${SCDS_ROOT:-/opt/sustainable-catalyst/decision-studio}"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
PERSIST_ENV="$ROOT/.env.persistence-v330"
SERVICE="${SCDS_COMPOSE_SERVICE:-decision-studio}"
DB_SERVICE="${SCDS_DB_SERVICE:-decision-studio-postgres}"
CONTAINER="${SCDS_CONTAINER:-sc-decision-studio}"
DB_CONTAINER="${SCDS_DB_CONTAINER:-sc-decision-studio-postgres}"
PORT="${SCDS_PORT:-8089}"
PUBLIC_URL="${SCDS_PUBLIC_URL:-https://decision-studio-api.sustainablecatalyst.com}"
BACKUP_ROOT="${SCDS_BACKUP_ROOT:-/opt/sustainable-catalyst/backups}"
REVISION="0001_v330_pg_foundation"
TMP="$(mktemp -d /tmp/sc-decision-studio-v3100.XXXXXX)"
SMOKE_DECISION=""
SMOKE_PROJECT=""
cleanup(){
  if [[ -n "$SMOKE_DECISION" ]] && docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
    docker exec "$DB_CONTAINER" sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -v ON_ERROR_STOP=1 -c \"DELETE FROM decisions WHERE id='${SMOKE_DECISION}'; DELETE FROM decision_projects WHERE id='${SMOKE_PROJECT}';\"" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP"
}
trap cleanup EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }
pass(){ echo "PASS: $*"; }

[[ -f "$ARCHIVE" ]] || fail "backend archive not found: $ARCHIVE"
[[ -d "$ROOT" && -f "$COMPOSE" ]] || fail "Decision Studio runtime root/compose missing: $ROOT"
for c in docker python3 unzip rsync curl tar; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
mkdir -p "$BACKUP_ROOT"
unzip -q "$ARCHIVE" -d "$TMP/archive"
SRC="$(find "$TMP/archive" -type f -path '*/backend/app/main.py' -print -quit | sed 's#/app/main.py$##')"
COMPOSE_TEMPLATE="$(find "$TMP/archive" -type f -name 'compose.v3.10.0.yml' -print -quit)"
[[ -n "$SRC" && -n "$COMPOSE_TEMPLATE" ]] || fail "could not locate v3.10 backend/compose payload"
for required in app/main.py app/api/router.py app/api/routes/composition.py app/cross_module_composition.py app/api/routes/module_registry.py app/unified_module_registry.py app/services/decision_service.py app/api/routes/repository.py app/api/routes/canvas.py app/api/routes/finance.py app/api/routes/narrative_risk.py app/api/routes/global_impact.py app/domains/canvas.py app/domains/finance.py app/domains/narrative_risk.py app/domains/global_impact.py app/persistence/database.py app/persistence/models.py app/persistence/contracts.py app/persistence/repository.py app/persistence/seed.py migrations/env.py migrations/versions/0001_v330_pg_foundation.py alembic.ini requirements.txt Dockerfile; do
  [[ -f "$SRC/$required" ]] || fail "v3.10 backend payload missing $required"
done
grep -q 'APP_VERSION = "3.10.0"' "$SRC/app/services/decision_service.py" || fail "payload is not Decision Studio v3.10.0"
grep -q 'scds-v3.10.0-cross-module-decision-composition' "$SRC/app/services/decision_service.py" || fail "v3.10 fingerprint missing"
grep -q 'CROSS_MODULE_COMPOSITION_SCHEMA = "scds-cross-module-decision-composition/1.0"' "$SRC/app/cross_module_composition.py" || fail "composition schema missing"
grep -q 'PERSISTENCE_AUTHORITY = "python-postgresql"' "$SRC/app/persistence/database.py" || fail "authoritative persistence boundary missing"
grep -q 'SCDS_PERSISTENCE_WRITE_ENABLED: "true"' "$COMPOSE_TEMPLATE" || fail "v3.10 compose does not preserve repository writes"

[[ -f "$PERSIST_ENV" ]] || fail "persistence credential file missing: $PERSIST_ENV"
for key in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD SCDS_DATABASE_URL SCDS_REPOSITORY_API_KEY; do grep -q "^${key}=" "$PERSIST_ENV" || fail "$PERSIST_ENV missing $key"; done
chmod 600 "$PERSIST_ENV"
set -a
# shellcheck disable=SC1090
source "$PERSIST_ENV"
set +a

echo "=== PRE-FLIGHT ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' || true
preflight="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
if [[ -n "$preflight" ]]; then
  python3 - "$preflight" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{})
assert x.get('version') in {'3.9.0','3.10.0'}, x
assert p.get('authority')=='python-postgresql' and p.get('authority_ready') is True, p
assert x.get('unified_decision_module_registry_schema')=='scds-unified-decision-module-registry/1.0',x
for key,schema in {
 'canvas_domain_schema':'scds-canvas-domain/1.0','finance_domain_schema':'scds-finance-domain/1.0',
 'narrative_risk_domain_schema':'scds-narrative-risk-domain/1.0','global_impact_domain_schema':'scds-global-impact-domain/1.0',
}.items(): assert x.get(key)==schema,(key,x.get(key))
PY
fi

stamp="$(date +%Y%m%d-%H%M%S)"
backup="$BACKUP_ROOT/decision-studio-before-v3.10.0-$stamp.tgz"
echo "=== BACKUP ==="
tar -czf "$backup" -C "$ROOT" backend compose.yml .env.persistence-v330
echo "$backup"

mkdir -p "$TMP/env"
for envfile in .env .env.production; do [[ -f "$LIVE_BACKEND/$envfile" ]] && cp -a "$LIVE_BACKEND/$envfile" "$TMP/env/$envfile"; done
rsync -a --delete --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='*.pyc' --exclude='.env' --exclude='.env.*' "$SRC/" "$LIVE_BACKEND/"
for envfile in .env .env.production; do [[ -f "$TMP/env/$envfile" ]] && cp -a "$TMP/env/$envfile" "$LIVE_BACKEND/$envfile"; done
cp "$COMPOSE_TEMPLATE" "$COMPOSE"
cd "$ROOT"
docker compose config --quiet

echo "=== VERIFY v3.9 FOUR-DOMAIN + UNIFIED REGISTRY BASELINE ==="
docker compose up -d "$DB_SERVICE"
for _ in $(seq 1 40); do
  if docker inspect -f '{{.State.Health.Status}}' "$DB_CONTAINER" 2>/dev/null | grep -q healthy; then break; fi
  sleep 2
done
[[ "$(docker inspect -f '{{.State.Health.Status}}' "$DB_CONTAINER" 2>/dev/null || true)" == "healthy" ]] || fail "PostgreSQL is not healthy"
current_rev="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version LIMIT 1"')"
[[ "$current_rev" == "$REVISION" ]] || fail "expected Alembic revision $REVISION, got $current_rev"
table_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema='"'"'public'"'"' AND table_name NOT IN ('"'"'alembic_version'"'"')"')"
[[ "$table_count" == "20" ]] || fail "expected 20 Decision Studio persistence tables, got $table_count"
module_state="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT module_id||'"'"':'"'"'||status FROM decision_modules ORDER BY module_id"')"
python3 - "$module_state" <<'PY'
import sys
rows=dict(line.split(':',1) for line in sys.argv[1].splitlines() if ':' in line)
assert set(rows)=={'canvas','finance','global-impact','narrative-risk'},rows
assert all(v=='python-domain-authoritative' for v in rows.values()),rows
PY
pass "v3.9 four-domain authority, Unified Registry, and 20-table schema are current"

echo "=== BUILD v3.10.0 ==="
docker compose build "$SERVICE"

echo "=== ALEMBIC NO-OP / HEAD VERIFICATION ==="
docker compose run --rm "$SERVICE" alembic upgrade head
post_rev="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version LIMIT 1"')"
[[ "$post_rev" == "$REVISION" ]] || fail "schema revision changed unexpectedly: $post_rev"

echo "=== REFRESH MODULE REGISTRY SEED ==="
docker compose run --rm "$SERVICE" python -m app.persistence.seed

echo "=== DEPLOY CROSS-MODULE DECISION COMPOSITION ==="
docker compose up -d "$SERVICE"
health=""
for _ in $(seq 1 45); do
  health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
  if [[ -n "$health" ]] && python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{}); a=x.get('release',{}).get('backend_architecture',{})
assert x.get('ok') is True and x.get('ready') is True
assert x.get('version')=='3.10.0'
assert x.get('build_fingerprint')=='scds-v3.10.0-cross-module-decision-composition'
assert x.get('source_commit')=='release-v3.10.0'
assert x.get('cross_module_decision_composition_schema')=='scds-cross-module-decision-composition/1.0'
assert p.get('connected') is True and p.get('schema_current') is True and p.get('authority_ready') is True
assert p.get('schema_revision')=='0001_v330_pg_foundation' and p.get('table_count')==20
assert a.get('database_migration') is False and a.get('cross_module_decision_composition') is True
assert a.get('route_count')==256 and a.get('router_registry_count')==20
PY
  then break; fi
  sleep 2
done
[[ -n "$health" ]] || { docker logs --tail=200 "$CONTAINER" >&2 || true; fail "backend did not answer /health"; }
python3 - "$health" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x['persistence']; a=x['release']['backend_architecture']; c=x['release']['cross_module_composition']
assert x['version']=='3.10.0',x
assert p['connected'] and p['schema_current'] and p['authority_ready'],p
assert p['table_count']==20 and p['authority']=='python-postgresql',p
assert a['route_count']==256 and a['router_registry_count']==20,a
assert a['database_migration'] is False and a['cross_module_decision_composition'] is True,a
assert c['schema']=='scds-cross-module-decision-composition/1.0' and c['explicit_links_only'] is True,c
assert c['module_ownership_preserved'] is True and c['final_decision_authority']=='human-governed',c
print('PASS: internal v3.10.0 health confirms governed Cross-Module Decision Composition')
PY

echo "=== COMPOSITION CONTRACT SMOKE ==="
contract="$(curl -fsS "http://127.0.0.1:${PORT}/decision-composition/contract")"
python3 - "$contract" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); c=x['composition_contract']; p=c['principles']
assert x['version']=='3.10.0' and c['schema']=='scds-cross-module-decision-composition/1.0',x
assert c['minimum_modules']==2 and set(c['canonical_modules'])=={'canvas','finance','narrative-risk','global-impact'},c
assert p['module_objects_retain_domain_ownership'] is True and p['composition_links_are_explicit_not_inferred'] is True,p
assert p['composition_does_not_infer_causality'] is True and p['composition_does_not_auto_recommend'] is True,p
assert c['compute_authorities']=={'finance':'workbench','global-impact':'workbench'},c
print('PASS: composition contract preserves module ownership, compute boundaries, and human governance')
PY

echo "=== AUTHORITATIVE FOUR-MODULE COMPOSITION + STALENESS SMOKE ==="
SMOKE_PROJECT="proj-v3100-smoke-$stamp"
SMOKE_DECISION="dec-v3100-smoke-$stamp"
H="x-scds-api-key: $SCDS_REPOSITORY_API_KEY"
curl -fsS -H "$H" -H 'content-type: application/json' -d "{\"project_id\":\"$SMOKE_PROJECT\",\"title\":\"v3.10 composition smoke\"}" "http://127.0.0.1:${PORT}/repository/projects" >/dev/null
curl -fsS -H "$H" -H 'content-type: application/json' -d "{\"decision_id\":\"$SMOKE_DECISION\",\"project_id\":\"$SMOKE_PROJECT\",\"decision_question\":\"v3.10 cross-module smoke\"}" "http://127.0.0.1:${PORT}/repository/decisions" >/dev/null
curl -fsS -X PUT -H "$H" -H 'content-type: application/json' -d '{"problem_statement":"Smoke","alternatives":[{"id":"alt-a","name":"A"}],"criteria":[{"id":"crit-a","name":"Resilience"}],"assumptions":[{"id":"asm-c","statement":"Canvas assumption"}]}' "http://127.0.0.1:${PORT}/canvas/decisions/$SMOKE_DECISION" >/dev/null
curl -fsS -X PUT -H "$H" -H 'content-type: application/json' -d '{"assumptions":[{"id":"asm-f","statement":"Finance assumption"}],"scenarios":[{"id":"fin-s1","name":"Base"}],"workbench_receipts":[{"id":"wb-1","label":"Finance run"}]}' "http://127.0.0.1:${PORT}/finance/decisions/$SMOKE_DECISION" >/dev/null
curl -fsS -X PUT -H "$H" -H 'content-type: application/json' -d '{"claims":[{"id":"risk-c1","text":"Supplier risk"}],"signals":[{"id":"risk-s1","label":"Lead time"}],"evidence_links":[{"id":"risk-e1","claim_ref":"risk-c1","evidence_ref":"evidence:risk"}]}' "http://127.0.0.1:${PORT}/narrative-risk/decisions/$SMOKE_DECISION" >/dev/null
curl -fsS -X PUT -H "$H" -H 'content-type: application/json' -d '{"impact_claims":[{"id":"impact-c1","text":"Lifecycle impact"}],"indicators":[{"id":"impact-i1","label":"Lifecycle carbon"}],"evidence_links":[{"id":"impact-e1","claim_ref":"impact-c1","evidence_ref":"evidence:impact"}]}' "http://127.0.0.1:${PORT}/global-impact/decisions/$SMOKE_DECISION" >/dev/null
composition="$(curl -fsS -X PUT -H "$H" -H 'content-type: application/json' -d '{"module_ids":["canvas","finance","narrative-risk","global-impact"],"title":"Smoke composition","cross_module_links":[{"relation":"tradeoff","source_module":"finance","source_ref":"wb-1","target_module":"global-impact","target_ref":"impact-i1"},{"relation":"risk-context","source_module":"narrative-risk","source_ref":"risk-c1","target_module":"canvas","target_ref":"alt-a"}]}' "http://127.0.0.1:${PORT}/decision-composition/decisions/$SMOKE_DECISION")"
python3 - "$composition" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); c=x['composition']; p=c['shared_kernel_projection']; d=c['diagnostics']
assert c['schema']=='scds-cross-module-decision-composition/1.0' and len(c['selected_modules'])==4,c
assert d['composition_ready'] is True and d['cross_module_link_count']==2,d
assert {x['module_id'] for x in p['assumptions']}=={'canvas','finance'},p['assumptions']
assert {x['module_id'] for x in p['claims']}=={'narrative-risk','global-impact'},p['claims']
assert {'finance','narrative-risk','global-impact'} <= {x['module_id'] for x in p['artifacts']},p['artifacts']
assert d['inferred_truth'] is False and d['inferred_causality'] is False and d['automatic_recommendation'] is False,d
print('PASS: authoritative four-module composition write/read and ownership projection succeeded')
PY
curl -fsS -X PUT -H "$H" -H 'content-type: application/json' -d '{"assumptions":[{"id":"asm-c2","statement":"Updated Canvas assumption"}]}' "http://127.0.0.1:${PORT}/canvas/decisions/$SMOKE_DECISION/assumptions" >/dev/null
stale="$(curl -fsS -H "$H" "http://127.0.0.1:${PORT}/decision-composition/decisions/$SMOKE_DECISION/diagnostics")"
python3 - "$stale" <<'PY'
import json,sys
x=json.loads(sys.argv[1])['diagnostics']
assert x['stale_modules']==['canvas'],x
print('PASS: module fingerprint diagnostics detect stale Canvas state')
PY
refreshed="$(curl -fsS -X POST -H "$H" "http://127.0.0.1:${PORT}/decision-composition/decisions/$SMOKE_DECISION/refresh")"
python3 - "$refreshed" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); c=x['composition']
assert x['refreshed'] is True and c['revision']==2,c
assert c['diagnostics']['composition_ready'] is True,c['diagnostics']
print('PASS: explicit composition refresh succeeded')
PY
fresh="$(curl -fsS -H "$H" "http://127.0.0.1:${PORT}/decision-composition/decisions/$SMOKE_DECISION/diagnostics")"
python3 - "$fresh" <<'PY'
import json,sys
x=json.loads(sys.argv[1])['diagnostics']; assert x['stale_modules']==[],x
print('PASS: refreshed composition fingerprints are current')
PY

echo "=== UNIFIED REGISTRY PRESERVATION ==="
readiness="$(curl -fsS "http://127.0.0.1:${PORT}/decision-module-registry/readiness")"
python3 - "$readiness" <<'PY'
import json,sys
r=json.loads(sys.argv[1])['readiness']
assert r['ready'] is True and r['all_modules_authoritative'] is True and r['module_count']==4,r
assert r['compute_authorities']=={'finance':'workbench','global-impact':'workbench'},r
print('PASS: canonical v3.9 Unified Decision Module Registry remains healthy')
PY

echo "=== PUBLIC CADDY CHECK ==="
public="$(curl -fsS "$PUBLIC_URL/health")"
python3 - "$public" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x['persistence']; c=x['release']['cross_module_composition']
assert x['version']=='3.10.0' and x['build_fingerprint']=='scds-v3.10.0-cross-module-decision-composition',x
assert x['cross_module_decision_composition_schema']=='scds-cross-module-decision-composition/1.0',x
assert p['connected'] and p['schema_current'] and p['authority']=='python-postgresql' and p['table_count']==20,p
assert c['explicit_links_only'] is True and c['module_ownership_preserved'] is True,c
print('PASS: public Decision Studio API returns v3.10.0 with governed Cross-Module Decision Composition')
PY
curl -fsS "$PUBLIC_URL/decision-composition/contract" | python3 -m json.tool

echo "=== CLEAN SYNTHETIC COMPOSITION RECORDS ==="
cleanup
SMOKE_DECISION=""
SMOKE_PROJECT=""

echo "=== FINAL CONTAINERS ==="
docker ps --filter "name=sc-decision-studio" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v3.10.0 deployed with governed Cross-Module Decision Composition"
echo "Backup: $backup"
echo "Persistence credentials: $PERSIST_ENV (mode 600; do not commit)"
