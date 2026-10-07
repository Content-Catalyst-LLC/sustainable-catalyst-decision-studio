#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="3.9.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v3.9.0.zip}"
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
TMP="$(mktemp -d /tmp/sc-decision-studio-v390.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }
pass(){ echo "PASS: $*"; }

[[ -f "$ARCHIVE" ]] || fail "backend archive not found: $ARCHIVE"
[[ -d "$ROOT" && -f "$COMPOSE" ]] || fail "Decision Studio runtime root/compose missing: $ROOT"
for c in docker python3 unzip rsync curl tar; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
mkdir -p "$BACKUP_ROOT"
unzip -q "$ARCHIVE" -d "$TMP/archive"
SRC="$(find "$TMP/archive" -type f -path '*/backend/app/main.py' -print -quit | sed 's#/app/main.py$##')"
COMPOSE_TEMPLATE="$(find "$TMP/archive" -type f -name 'compose.v3.9.0.yml' -print -quit)"
[[ -n "$SRC" && -n "$COMPOSE_TEMPLATE" ]] || fail "could not locate v3.9 backend/compose payload"
for required in app/main.py app/api/router.py app/api/routes/module_registry.py app/unified_module_registry.py app/services/decision_service.py app/api/routes/repository.py app/api/routes/canvas.py app/api/routes/finance.py app/api/routes/narrative_risk.py app/api/routes/global_impact.py app/domains/canvas.py app/domains/finance.py app/domains/narrative_risk.py app/domains/global_impact.py app/persistence/database.py app/persistence/models.py app/persistence/contracts.py app/persistence/repository.py app/persistence/seed.py migrations/env.py migrations/versions/0001_v330_pg_foundation.py alembic.ini requirements.txt Dockerfile; do
  [[ -f "$SRC/$required" ]] || fail "v3.9 backend payload missing $required"
done
grep -q 'APP_VERSION = "3.9.0"' "$SRC/app/services/decision_service.py" || fail "payload is not Decision Studio v3.9.0"
grep -q 'scds-v3.9.0-unified-decision-module-registry' "$SRC/app/services/decision_service.py" || fail "v3.9 fingerprint missing"
grep -q 'UNIFIED_DECISION_MODULE_REGISTRY_SCHEMA = "scds-unified-decision-module-registry/1.0"' "$SRC/app/unified_module_registry.py" || fail "unified registry schema missing"
grep -q 'PERSISTENCE_AUTHORITY = "python-postgresql"' "$SRC/app/persistence/database.py" || fail "authoritative persistence boundary missing"
grep -q 'SCDS_PERSISTENCE_WRITE_ENABLED: "true"' "$COMPOSE_TEMPLATE" || fail "v3.9 compose does not preserve repository writes"

[[ -f "$PERSIST_ENV" ]] || fail "persistence credential file missing: $PERSIST_ENV"
for key in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD SCDS_DATABASE_URL SCDS_REPOSITORY_API_KEY; do grep -q "^${key}=" "$PERSIST_ENV" || fail "$PERSIST_ENV missing $key"; done
chmod 600 "$PERSIST_ENV"

echo "=== PRE-FLIGHT ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' || true
preflight="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
if [[ -n "$preflight" ]]; then
  python3 - "$preflight" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{})
assert x.get('version') in {'3.8.0','3.9.0'}, x
assert p.get('authority')=='python-postgresql' and p.get('authority_ready') is True, p
for key,schema in {
 'canvas_domain_schema':'scds-canvas-domain/1.0',
 'finance_domain_schema':'scds-finance-domain/1.0',
 'narrative_risk_domain_schema':'scds-narrative-risk-domain/1.0',
 'global_impact_domain_schema':'scds-global-impact-domain/1.0',
}.items(): assert x.get(key)==schema,(key,x.get(key))
PY
fi

stamp="$(date +%Y%m%d-%H%M%S)"
backup="$BACKUP_ROOT/decision-studio-before-v3.9.0-$stamp.tgz"
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

echo "=== VERIFY v3.8 FOUR-DOMAIN + REPOSITORY BASELINE ==="
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
pass "v3.8 four-domain authoritative repository and 20-table schema are current"

echo "=== BUILD v3.9.0 ==="
docker compose build "$SERVICE"

echo "=== ALEMBIC NO-OP / HEAD VERIFICATION ==="
docker compose run --rm "$SERVICE" alembic upgrade head
post_rev="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version LIMIT 1"')"
[[ "$post_rev" == "$REVISION" ]] || fail "schema revision changed unexpectedly: $post_rev"

echo "=== REFRESH MODULE REGISTRY SEED ==="
docker compose run --rm "$SERVICE" python -m app.persistence.seed

echo "=== DEPLOY UNIFIED DECISION MODULE REGISTRY ==="
docker compose up -d "$SERVICE"
health=""
for _ in $(seq 1 45); do
  health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
  if [[ -n "$health" ]] && python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{}); a=x.get('release',{}).get('backend_architecture',{})
assert x.get('ok') is True and x.get('ready') is True
assert x.get('version')=='3.9.0'
assert x.get('build_fingerprint')=='scds-v3.9.0-unified-decision-module-registry'
assert x.get('source_commit')=='release-v3.9.0'
assert x.get('unified_decision_module_registry_schema')=='scds-unified-decision-module-registry/1.0'
assert p.get('connected') is True and p.get('schema_current') is True and p.get('authority_ready') is True
assert p.get('schema_revision')=='0001_v330_pg_foundation' and p.get('table_count')==20
assert a.get('database_migration') is False and a.get('unified_decision_module_registry') is True
assert a.get('route_count')==249 and a.get('router_registry_count')==19
PY
  then break; fi
  sleep 2
done
[[ -n "$health" ]] || { docker logs --tail=200 "$CONTAINER" >&2 || true; fail "backend did not answer /health"; }
python3 - "$health" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x['persistence']; a=x['release']['backend_architecture']; u=x['release']['unified_module_registry']
assert x['version']=='3.9.0',x
assert p['connected'] and p['schema_current'] and p['authority_ready'],p
assert p['table_count']==20 and p['authority']=='python-postgresql',p
assert a['route_count']==249 and a['router_registry_count']==19,a
assert a['database_migration'] is False and a['unified_registry_canonical'] is True,a
assert u['schema']=='scds-unified-decision-module-registry/1.0' and u['canonical'] is True,u
assert u['module_count']==4 and u['all_modules_authoritative'] is True,u
print('PASS: internal v3.9.0 health confirms canonical Unified Decision Module Registry')
PY

echo "=== UNIFIED REGISTRY CONTRACT SMOKE ==="
registry="$(curl -fsS "http://127.0.0.1:${PORT}/decision-module-registry")"
python3 - "$registry" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); r=x['registry']; mods={m['module_id']:m for m in r['modules']}
assert x['version']=='3.9.0' and r['schema']=='scds-unified-decision-module-registry/1.0',x
assert r['registry_authority']=='decision-studio-kernel' and r['module_count']==4,r
assert set(mods)=={'canvas','finance','narrative-risk','global-impact'},mods
for mid,m in mods.items():
    assert m['status']=='python-domain-authoritative',m
    assert m['authority']['storage']=='python-postgresql',m
    assert m['security']['read_scope'] and m['security']['write_scope'],m
assert mods['finance']['authority']['compute']=='workbench'
assert mods['global-impact']['authority']['compute']=='workbench'
assert r['compatibility']['legacy_decision_modules_endpoints_preserved'] is True
assert r['governance']['registry_does_not_auto_recommend'] is True
assert r['governance']['final_decision_authority']=='human-governed'
print('PASS: unified registry exposes all four authoritative modules and governance boundaries')
PY

echo "=== PROVIDER / CAPABILITY / READINESS INDEX SMOKE ==="
providers="$(curl -fsS "http://127.0.0.1:${PORT}/decision-module-registry/providers")"
capabilities="$(curl -fsS "http://127.0.0.1:${PORT}/decision-module-registry/capabilities")"
readiness="$(curl -fsS "http://127.0.0.1:${PORT}/decision-module-registry/readiness")"
python3 - "$providers" "$capabilities" "$readiness" <<'PY'
import json,sys
p,c,r=map(json.loads,sys.argv[1:])
pmap={x['provider']:x for x in p['provider_index']['providers']}
assert 'workbench' in pmap and {'finance','global-impact'} <= set(pmap['workbench']['modules'])
assert 'compute_authority' in pmap['workbench']['roles']
caps={x['capability']:x['modules'] for x in c['capability_index']['capabilities']}
assert caps['financial-scenarios']==['finance']
assert caps['contradiction-tracing']==['narrative-risk']
assert caps['sdg-alignment']==['global-impact']
ready=r['readiness']
assert ready['ready'] is True and ready['all_modules_authoritative'] is True and ready['persistence_ready'] is True,ready
assert ready['compute_authorities']=={'finance':'workbench','global-impact':'workbench'},ready
print('PASS: provider, capability, and live readiness indexes are coherent')
PY

echo "=== LEGACY MODULE REGISTRY COMPATIBILITY ==="
legacy="$(curl -fsS "http://127.0.0.1:${PORT}/decision-modules")"
python3 - "$legacy" "$registry" <<'PY'
import json,sys
old=json.loads(sys.argv[1])['registry']; new=json.loads(sys.argv[2])['registry']
assert old['module_count']==new['module_count']==4
assert {m['module_id'] for m in old['modules']}==set(new['module_ids'])
print('PASS: legacy /decision-modules registry remains compatible with canonical v3.9 registry')
PY

echo "=== PUBLIC CADDY CHECK ==="
public="$(curl -fsS "$PUBLIC_URL/health")"
python3 - "$public" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x['persistence']; u=x['release']['unified_module_registry']
assert x['version']=='3.9.0' and x['build_fingerprint']=='scds-v3.9.0-unified-decision-module-registry',x
assert x['unified_decision_module_registry_schema']=='scds-unified-decision-module-registry/1.0',x
assert p['connected'] and p['schema_current'] and p['authority']=='python-postgresql',p
assert p['write_enabled'] is True and p['authority_ready'] is True,p
assert u['canonical'] is True and u['module_count']==4 and u['all_modules_authoritative'] is True,u
print('PASS: public Decision Studio API returns v3.9.0 with canonical Unified Decision Module Registry')
PY
curl -fsS "$PUBLIC_URL/decision-module-registry/readiness" | python3 -m json.tool

echo "=== FINAL CONTAINERS ==="
docker ps --filter "name=sc-decision-studio" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v3.9.0 deployed with canonical Unified Decision Module Registry"
echo "Backup: $backup"
echo "Persistence credentials: $PERSIST_ENV (mode 600; do not commit)"
