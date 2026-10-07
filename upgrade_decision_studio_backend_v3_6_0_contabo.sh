#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="3.6.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v3.6.0.zip}"
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
TMP="$(mktemp -d /tmp/sc-decision-studio-v360.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }
pass(){ echo "PASS: $*"; }

[[ -f "$ARCHIVE" ]] || fail "backend archive not found: $ARCHIVE"
[[ -d "$ROOT" && -f "$COMPOSE" ]] || fail "Decision Studio runtime root/compose missing: $ROOT"
for c in docker python3 unzip rsync curl tar; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
mkdir -p "$BACKUP_ROOT"
unzip -q "$ARCHIVE" -d "$TMP/archive"
SRC="$(find "$TMP/archive" -type f -path '*/backend/app/main.py' -print -quit | sed 's#/app/main.py$##')"
COMPOSE_TEMPLATE="$(find "$TMP/archive" -type f -name 'compose.v3.6.0.yml' -print -quit)"
[[ -n "$SRC" && -n "$COMPOSE_TEMPLATE" ]] || fail "could not locate v3.6 backend/compose payload"
for required in app/main.py app/api/router.py app/api/routes/repository.py app/api/routes/canvas.py app/api/routes/finance.py app/services/decision_service.py app/domains/canvas.py app/domains/finance.py app/persistence/database.py app/persistence/models.py app/persistence/contracts.py app/persistence/repository.py app/persistence/seed.py migrations/env.py migrations/versions/0001_v330_pg_foundation.py alembic.ini requirements.txt Dockerfile; do
  [[ -f "$SRC/$required" ]] || fail "v3.6 backend payload missing $required"
done
grep -q 'APP_VERSION = "3.6.0"' "$SRC/app/services/decision_service.py" || fail "payload is not Decision Studio v3.6.0"
grep -q 'scds-v3.6.0-finance-python-domain-migration' "$SRC/app/services/decision_service.py" || fail "v3.6 fingerprint missing"
grep -q 'FINANCE_DOMAIN_SCHEMA = "scds-finance-domain/1.0"' "$SRC/app/domains/finance.py" || fail "Finance domain schema missing"
grep -q 'CANVAS_DOMAIN_SCHEMA = "scds-canvas-domain/1.0"' "$SRC/app/domains/canvas.py" || fail "Canvas domain preservation missing"
grep -q 'PERSISTENCE_AUTHORITY = "python-postgresql"' "$SRC/app/persistence/database.py" || fail "authoritative persistence boundary missing"
grep -q 'SCDS_PERSISTENCE_WRITE_ENABLED: "true"' "$COMPOSE_TEMPLATE" || fail "v3.6 compose does not preserve repository writes"

echo "=== PRE-FLIGHT ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' || true
preflight="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
if [[ -n "$preflight" ]]; then
  python3 - "$preflight" <<'PY'
import json,sys
x=json.loads(sys.argv[1])
assert x.get('version') in {'3.5.0','3.6.0'}, x
p=x.get('persistence',{})
assert p.get('authority')=='python-postgresql' and p.get('authority_ready') is True, p
if x.get('version')=='3.5.0':
    assert x.get('canvas_domain_schema')=='scds-canvas-domain/1.0', x
PY
fi
[[ -f "$PERSIST_ENV" ]] || fail "persistence credential file missing: $PERSIST_ENV"
for key in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD SCDS_DATABASE_URL SCDS_REPOSITORY_API_KEY; do grep -q "^${key}=" "$PERSIST_ENV" || fail "$PERSIST_ENV missing $key"; done
chmod 600 "$PERSIST_ENV"
REPO_API_KEY="$(grep '^SCDS_REPOSITORY_API_KEY=' "$PERSIST_ENV" | tail -1 | cut -d= -f2-)"
[[ -n "$REPO_API_KEY" ]] || fail "repository API key is empty"

stamp="$(date +%Y%m%d-%H%M%S)"
backup="$BACKUP_ROOT/decision-studio-before-v3.6.0-$stamp.tgz"
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

echo "=== VERIFY v3.5 CANVAS + REPOSITORY BASELINE ==="
docker compose up -d "$DB_SERVICE"
for _ in $(seq 1 60); do
  if docker exec "$DB_CONTAINER" sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then break; fi
  sleep 2
done
docker exec "$DB_CONTAINER" sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1 || fail "PostgreSQL did not become ready"
current_revision="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version LIMIT 1"' || true)"
[[ "$current_revision" == "$REVISION" ]] || fail "v3.6 requires revision $REVISION; found ${current_revision:-<none>}"
table_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema='"'"'public'"'"' AND table_type='"'"'BASE TABLE'"'"' AND table_name <> '"'"'alembic_version'"'"'"')"
[[ "$table_count" == "20" ]] || fail "expected 20 persistence tables, got $table_count"
canvas_status="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT status FROM decision_modules WHERE module_id='"'"'canvas'"'"'"' || true)"
[[ "$canvas_status" == "python-domain-authoritative" ]] || fail "v3.6 requires v3.5 Canvas authority; found $canvas_status"
pass "v3.5 Canvas + authoritative repository baseline is current"

echo "=== BUILD v3.6.0 BACKEND ==="
docker compose build "$SERVICE"

echo "=== ALEMBIC NO-OP / HEAD VERIFICATION ==="
docker compose run --rm "$SERVICE" alembic upgrade head
revision="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version LIMIT 1"')"
[[ "$revision" == "$REVISION" ]] || fail "schema revision changed unexpectedly: $revision"

echo "=== REFRESH MODULE REGISTRY ==="
docker compose run --rm "$SERVICE" python -m app.persistence.seed
canvas_status="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT status FROM decision_modules WHERE module_id='"'"'canvas'"'"'"')"
finance_status="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT status FROM decision_modules WHERE module_id='"'"'finance'"'"'"')"
[[ "$canvas_status" == "python-domain-authoritative" ]] || fail "Canvas authority regressed: $canvas_status"
[[ "$finance_status" == "python-domain-authoritative" ]] || fail "Finance module registry status not migrated: $finance_status"
pass "Canvas and Finance module registry statuses are python-domain-authoritative"

echo "=== DEPLOY FINANCE PYTHON DOMAIN ==="
docker compose up -d --force-recreate "$SERVICE"
health=""
for _ in $(seq 1 60); do
  if health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null)"; then
    if python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{}); a=x.get('release',{}).get('backend_architecture',{})
assert x.get('ok') is True and x.get('ready') is True
assert x.get('version')=='3.6.0'
assert x.get('build_fingerprint')=='scds-v3.6.0-finance-python-domain-migration'
assert x.get('source_commit')=='release-v3.6.0'
assert x.get('canvas_domain_schema')=='scds-canvas-domain/1.0'
assert x.get('finance_domain_schema')=='scds-finance-domain/1.0'
assert p.get('connected') is True and p.get('schema_current') is True and p.get('authority_ready') is True
assert p.get('schema_revision')=='0001_v330_pg_foundation' and p.get('table_count')==20
assert a.get('database_migration') is False and a.get('finance_python_domain_migration') is True
PY
    then break; fi
  fi
  sleep 2
done
[[ -n "$health" ]] || { docker logs --tail=200 "$CONTAINER" >&2 || true; fail "backend did not answer /health"; }
python3 - "$health" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x['persistence']; a=x['release']['backend_architecture']; f=x['release']['finance']; c=x['release']['canvas']
assert x['version']=='3.6.0',x
assert p['connected'] and p['schema_current'] and p['authority_ready'],p
assert p['table_count']==20 and p['authority']=='python-postgresql',p
assert a['route_count']==220 and a['router_registry_count']==16,a
assert a['database_migration'] is False and a['finance_python_domain_migration'] is True,a
assert f['schema']=='scds-finance-domain/1.0' and f['status']=='python-domain-authoritative',f
assert f['compute_authority']=='workbench' and f['decision_studio_executes_financial_models'] is False,f
assert c['status']=='python-domain-authoritative',c
print('PASS: internal v3.6.0 health confirms Finance Python domain migration')
PY

echo "=== FINANCE CONTRACT SMOKE ==="
finance_contract="$(curl -fsS "http://127.0.0.1:${PORT}/finance/contract")"
python3 - "$finance_contract" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); f=x['finance_contract']; b=f['boundaries']
assert x['version']=='3.6.0' and f['schema']=='scds-finance-domain/1.0',x
assert f['status']=='python-domain-authoritative' and f['storage_authority']=='python-postgresql',f
assert f['compute_authority']=='workbench' and b['workbench_is_compute_authority'] is True,f
assert b['decision_studio_executes_financial_models'] is False
assert b['model_output_is_automatic_recommendation'] is False
assert b['final_decision_authority']=='human-governed'
print('PASS: Finance domain contract is live with Workbench compute authority')
PY

echo "=== AUTHORITATIVE FINANCE WRITE/READ + DOMAIN ISOLATION SMOKE ==="
docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "DELETE FROM decisions WHERE id='"'"'v360-deploy-smoke-decision'"'"'; DELETE FROM decision_projects WHERE id='"'"'v360-deploy-smoke-project'"'"';"' >/dev/null
curl -fsS -X POST "http://127.0.0.1:${PORT}/repository/projects" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"project_id":"v360-deploy-smoke-project","title":"v3.6 Finance deployment smoke"}' >/dev/null
curl -fsS -X POST "http://127.0.0.1:${PORT}/repository/decisions" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"decision_id":"v360-deploy-smoke-decision","project_id":"v360-deploy-smoke-project","decision_question":"Which finance pathway should be reviewed?"}' >/dev/null
# Establish Canvas-owned shared-table row first.
curl -fsS -X PUT "http://127.0.0.1:${PORT}/canvas/decisions/v360-deploy-smoke-decision" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"assumptions":[{"id":"canvas-a","statement":"Canvas-owned deployment assumption"}]}' >/dev/null
finance_write="$(curl -fsS -X PUT "http://127.0.0.1:${PORT}/finance/decisions/v360-deploy-smoke-decision" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"currency":"USD","base_year":2026,"horizon_years":8,"capital_context":{"capex_ref":"workbench:input:capex"},"discounting_context":{"discount_rate_ref":"workbench:input:wacc"},"model_refs":["workbench:model:dcf"],"assumptions":[{"id":"finance-a","statement":"Finance-owned deployment assumption","confidence":"test"}],"scenarios":[{"id":"base","name":"Base case","variables":[{"id":"price","name":"Energy price","value":{"amount":80,"unit":"USD/MWh"}}]}],"uncertainty_models":[{"id":"u1","model_type":"financial-input-uncertainty","specification":{"variable":"capex"},"computation_ref":"workbench:uncertainty:u1"}],"workbench_receipts":[{"id":"r1","uri":"workbench://jobs/v360-smoke","metadata":{"result_kind":"valuation"}}],"provenance":{"source":"deploy-v3.6.0"}}')"
finance_read="$(curl -fsS "http://127.0.0.1:${PORT}/finance/decisions/v360-deploy-smoke-decision" -H "X-SCDS-API-Key: $REPO_API_KEY")"
python3 - "$finance_write" "$finance_read" <<'PY'
import json,sys
w,r=map(json.loads,sys.argv[1:])
for x in (w,r):
    f=x['finance']
    assert f['schema']=='scds-finance-domain/1.0'
    assert len(f['assumptions'])==1 and len(f['scenarios'])==1 and len(f['uncertainty_models'])==1 and len(f['workbench_receipts'])==1
    assert f['authorities']['compute_authority']=='workbench'
    assert f['boundaries']['decision_studio_executes_financial_models'] is False
print('PASS: authoritative Finance write/read round trip succeeded')
PY
# Update Canvas again; Finance assumption must survive.
curl -fsS -X PUT "http://127.0.0.1:${PORT}/canvas/decisions/v360-deploy-smoke-decision/assumptions" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"assumptions":[{"id":"canvas-b","statement":"Updated Canvas-owned deployment assumption"}]}' >/dev/null
finance_asm="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM assumptions WHERE decision_id='"'"'v360-deploy-smoke-decision'"'"' AND metadata_json->>'"'"'domain'"'"'='"'"'finance'"'"'"')"
canvas_asm="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM assumptions WHERE decision_id='"'"'v360-deploy-smoke-decision'"'"' AND metadata_json->>'"'"'domain'"'"'='"'"'canvas'"'"'"')"
scenario_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM scenarios WHERE decision_id='"'"'v360-deploy-smoke-decision'"'"' AND metadata_json->>'"'"'domain'"'"'='"'"'finance'"'"'"')"
uncertainty_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM uncertainty_models WHERE decision_id='"'"'v360-deploy-smoke-decision'"'"' AND specification->>'"'"'domain'"'"'='"'"'finance'"'"'"')"
receipt_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM artifacts WHERE decision_id='"'"'v360-deploy-smoke-decision'"'"' AND artifact_type='"'"'finance-workbench-receipt'"'"'"')"
[[ "$finance_asm" == "1" && "$canvas_asm" == "1" && "$scenario_count" == "1" && "$uncertainty_count" == "1" && "$receipt_count" == "1" ]] || fail "Finance normalized/domain isolation counts invalid: finance_assumptions=$finance_asm canvas_assumptions=$canvas_asm scenarios=$scenario_count uncertainty=$uncertainty_count receipts=$receipt_count"
pass "Finance shared-table normalization and Canvas/Finance ownership isolation verified"
docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "DELETE FROM decisions WHERE id='"'"'v360-deploy-smoke-decision'"'"'; DELETE FROM decision_projects WHERE id='"'"'v360-deploy-smoke-project'"'"';"' >/dev/null

echo "=== MODULE AUTHORITY BOUNDARIES ==="
mods="$(curl -fsS "http://127.0.0.1:${PORT}/decision-modules")"
python3 - "$mods" <<'PY'
import json,sys
r=json.loads(sys.argv[1])['registry']; mods={m['module_id']:m for m in r['modules']}
assert r['module_count']==4 and set(mods)=={'canvas','finance','narrative-risk','global-impact'},r
assert mods['canvas']['status']=='python-domain-authoritative' and mods['canvas']['storage_authority']=='python-postgresql',mods['canvas']
assert mods['finance']['status']=='python-domain-authoritative' and mods['finance']['storage_authority']=='python-postgresql',mods['finance']
assert mods['finance']['providers']['compute_authority']=='workbench',mods['finance']
assert mods['narrative-risk']['status']=='foundation' and mods['global-impact']['status']=='foundation'
print('PASS: Canvas + Finance authoritative; Narrative Risk + Global Impact remain staged; Workbench retains Finance compute authority')
PY

echo "=== PUBLIC CADDY CHECK ==="
public="$(curl -fsS "$PUBLIC_URL/health")"
python3 - "$public" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x['persistence']; f=x['release']['finance']
assert x['version']=='3.6.0' and x['build_fingerprint']=='scds-v3.6.0-finance-python-domain-migration',x
assert x['finance_domain_schema']=='scds-finance-domain/1.0',x
assert p['connected'] and p['schema_current'] and p['authority']=='python-postgresql',p
assert p['write_enabled'] is True and p['authority_ready'] is True,p
assert f['compute_authority']=='workbench' and f['decision_studio_executes_financial_models'] is False,f
print('PASS: public Decision Studio API returns v3.6.0 with authoritative Finance domain')
PY
curl -fsS "$PUBLIC_URL/finance/contract" | python3 -m json.tool

echo "=== FINAL CONTAINERS ==="
docker ps --filter "name=sc-decision-studio" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v3.6.0 deployed with Finance Python domain authority and Workbench compute authority"
echo "Backup: $backup"
echo "Persistence credentials: $PERSIST_ENV (mode 600; do not commit)"
