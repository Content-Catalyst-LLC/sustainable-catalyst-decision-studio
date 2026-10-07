#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="3.5.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v3.5.0.zip}"
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
TMP="$(mktemp -d /tmp/sc-decision-studio-v350.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }
pass(){ echo "PASS: $*"; }

[[ -f "$ARCHIVE" ]] || fail "backend archive not found: $ARCHIVE"
[[ -d "$ROOT" && -f "$COMPOSE" ]] || fail "Decision Studio runtime root/compose missing: $ROOT"
for c in docker python3 unzip rsync curl tar; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
mkdir -p "$BACKUP_ROOT"
unzip -q "$ARCHIVE" -d "$TMP/archive"
SRC="$(find "$TMP/archive" -type f -path '*/backend/app/main.py' -print -quit | sed 's#/app/main.py$##')"
COMPOSE_TEMPLATE="$(find "$TMP/archive" -type f -name 'compose.v3.5.0.yml' -print -quit)"
[[ -n "$SRC" && -n "$COMPOSE_TEMPLATE" ]] || fail "could not locate v3.5 backend/compose payload"
for required in app/main.py app/api/router.py app/api/routes/repository.py app/api/routes/canvas.py app/services/decision_service.py app/domains/canvas.py app/persistence/database.py app/persistence/models.py app/persistence/contracts.py app/persistence/repository.py app/persistence/seed.py migrations/env.py migrations/versions/0001_v330_pg_foundation.py alembic.ini requirements.txt Dockerfile; do
  [[ -f "$SRC/$required" ]] || fail "v3.5 backend payload missing $required"
done
grep -q 'APP_VERSION = "3.5.0"' "$SRC/app/services/decision_service.py" || fail "payload is not Decision Studio v3.5.0"
grep -q 'scds-v3.5.0-canvas-python-domain-migration' "$SRC/app/services/decision_service.py" || fail "v3.5 fingerprint missing"
grep -q 'CANVAS_DOMAIN_SCHEMA = "scds-canvas-domain/1.0"' "$SRC/app/domains/canvas.py" || fail "Canvas domain schema missing"
grep -q 'PERSISTENCE_AUTHORITY = "python-postgresql"' "$SRC/app/persistence/database.py" || fail "authoritative persistence boundary missing"
grep -q 'SCDS_PERSISTENCE_WRITE_ENABLED: "true"' "$COMPOSE_TEMPLATE" || fail "v3.5 compose does not preserve repository writes"

echo "=== PRE-FLIGHT ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' || true
preflight="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
if [[ -n "$preflight" ]]; then
  python3 - "$preflight" <<'PY'
import json,sys
x=json.loads(sys.argv[1])
assert x.get('version') in {'3.4.0','3.5.0'}, x
p=x.get('persistence',{})
assert p.get('authority')=='python-postgresql' and p.get('authority_ready') is True, p
PY
fi
[[ -f "$PERSIST_ENV" ]] || fail "persistence credential file missing: $PERSIST_ENV"
for key in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD SCDS_DATABASE_URL SCDS_REPOSITORY_API_KEY; do grep -q "^${key}=" "$PERSIST_ENV" || fail "$PERSIST_ENV missing $key"; done
chmod 600 "$PERSIST_ENV"
REPO_API_KEY="$(grep '^SCDS_REPOSITORY_API_KEY=' "$PERSIST_ENV" | tail -1 | cut -d= -f2-)"
[[ -n "$REPO_API_KEY" ]] || fail "repository API key is empty"

stamp="$(date +%Y%m%d-%H%M%S)"
backup="$BACKUP_ROOT/decision-studio-before-v3.5.0-$stamp.tgz"
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

echo "=== VERIFY v3.4 REPOSITORY FOUNDATION ==="
docker compose up -d "$DB_SERVICE"
for _ in $(seq 1 60); do
  if docker exec "$DB_CONTAINER" sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then break; fi
  sleep 2
done
docker exec "$DB_CONTAINER" sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1 || fail "PostgreSQL did not become ready"
current_revision="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version LIMIT 1"' || true)"
[[ "$current_revision" == "$REVISION" ]] || fail "v3.5 requires revision $REVISION; found ${current_revision:-<none>}"
table_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema='"'"'public'"'"' AND table_type='"'"'BASE TABLE'"'"' AND table_name <> '"'"'alembic_version'"'"'"')"
[[ "$table_count" == "20" ]] || fail "expected 20 persistence tables, got $table_count"
pass "v3.4 authoritative repository foundation is current"

echo "=== BUILD v3.5.0 BACKEND ==="
docker compose build "$SERVICE"

echo "=== ALEMBIC NO-OP / HEAD VERIFICATION ==="
docker compose run --rm "$SERVICE" alembic upgrade head
revision="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version LIMIT 1"')"
[[ "$revision" == "$REVISION" ]] || fail "schema revision changed unexpectedly: $revision"

echo "=== REFRESH MODULE REGISTRY ==="
docker compose run --rm "$SERVICE" python -m app.persistence.seed
canvas_status="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT status FROM decision_modules WHERE module_id='"'"'canvas'"'"'"')"
[[ "$canvas_status" == "python-domain-authoritative" ]] || fail "Canvas module registry status not migrated: $canvas_status"
pass "Canvas module registry is python-domain-authoritative"

echo "=== DEPLOY CANVAS PYTHON DOMAIN ==="
docker compose up -d --force-recreate "$SERVICE"
health=""
for _ in $(seq 1 60); do
  if health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null)"; then
    if python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{}); a=x.get('release',{}).get('backend_architecture',{})
assert x.get('ok') is True and x.get('ready') is True
assert x.get('version')=='3.5.0'
assert x.get('build_fingerprint')=='scds-v3.5.0-canvas-python-domain-migration'
assert x.get('source_commit')=='release-v3.5.0'
assert x.get('canvas_domain_schema')=='scds-canvas-domain/1.0'
assert p.get('connected') is True and p.get('schema_current') is True and p.get('authority_ready') is True
assert p.get('schema_revision')=='0001_v330_pg_foundation' and p.get('table_count')==20
assert a.get('database_migration') is False and a.get('canvas_python_domain_migration') is True
PY
    then break; fi
  fi
  sleep 2
done
[[ -n "$health" ]] || { docker logs --tail=200 "$CONTAINER" >&2 || true; fail "backend did not answer /health"; }
python3 - "$health" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x['persistence']; a=x['release']['backend_architecture']; c=x['release']['canvas']
assert x['version']=='3.5.0',x
assert p['connected'] and p['schema_current'] and p['authority_ready'],p
assert p['table_count']==20 and p['authority']=='python-postgresql',p
assert a['route_count']==209 and a['router_registry_count']==15,a
assert a['database_migration'] is False and a['canvas_python_domain_migration'] is True,a
assert c['schema']=='scds-canvas-domain/1.0' and c['status']=='python-domain-authoritative',c
assert c['final_decision_authority']=='human-governed',c
print('PASS: internal v3.5.0 health confirms Canvas Python domain migration')
PY

echo "=== CANVAS CONTRACT SMOKE ==="
canvas_contract="$(curl -fsS "http://127.0.0.1:${PORT}/canvas/contract")"
python3 - "$canvas_contract" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); c=x['canvas_contract']; b=c['boundaries']
assert x['version']=='3.5.0' and c['schema']=='scds-canvas-domain/1.0',x
assert c['status']=='python-domain-authoritative' and c['storage_authority']=='python-postgresql',c
assert b['shared_decision_identity_owned_by_kernel'] is True
assert b['automatic_winner_selection'] is False and b['automatic_recommendation'] is False
assert b['final_decision_authority']=='human-governed'
print('PASS: Canvas domain contract is live')
PY

echo "=== AUTHORITATIVE CANVAS WRITE/READ SMOKE ==="
docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "DELETE FROM decisions WHERE id='"'"'v350-deploy-smoke-decision'"'"'; DELETE FROM decision_projects WHERE id='"'"'v350-deploy-smoke-project'"'"';"' >/dev/null
curl -fsS -X POST "http://127.0.0.1:${PORT}/repository/projects" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"project_id":"v350-deploy-smoke-project","title":"v3.5 Canvas deployment smoke"}' >/dev/null
curl -fsS -X POST "http://127.0.0.1:${PORT}/repository/decisions" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"decision_id":"v350-deploy-smoke-decision","project_id":"v350-deploy-smoke-project","decision_question":"Which Canvas pathway should be reviewed?"}' >/dev/null
canvas_write="$(curl -fsS -X PUT "http://127.0.0.1:${PORT}/canvas/decisions/v350-deploy-smoke-decision" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"problem_statement":"Deployment smoke framing","decision_question":"Which Canvas pathway should be reviewed?","objective":"Verify Canvas persistence","constraints":["synthetic smoke only"],"stakeholders":[{"role":"reviewer","name":"deployment"}],"alternatives":[{"id":"a","name":"Path A"},{"id":"b","name":"Path B"}],"criteria":[{"id":"cost","name":"Cost","weight":0.4,"direction":"lower"},{"id":"impact","name":"Impact","weight":0.6,"direction":"higher"}],"assumptions":[{"id":"a1","statement":"Synthetic deployment assumption","confidence":"test"}],"provenance":{"source":"deploy-v3.5.0"}}')"
canvas_read="$(curl -fsS "http://127.0.0.1:${PORT}/canvas/decisions/v350-deploy-smoke-decision" -H "X-SCDS-API-Key: $REPO_API_KEY")"
python3 - "$canvas_write" "$canvas_read" <<'PY'
import json,sys
w,r=map(json.loads,sys.argv[1:])
for x in (w,r):
    c=x['canvas']
    assert c['schema']=='scds-canvas-domain/1.0'
    assert len(c['alternatives'])==2 and len(c['criteria'])==2 and len(c['assumptions'])==1
    assert c['boundaries']['automatic_winner_selection'] is False
    assert c['boundaries']['final_decision_authority']=='human-governed'
print('PASS: authoritative Canvas write/read round trip succeeded')
PY
alt_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM alternatives WHERE decision_id='"'"'v350-deploy-smoke-decision'"'"'"')"
crit_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM criteria WHERE decision_id='"'"'v350-deploy-smoke-decision'"'"'"')"
asm_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM assumptions WHERE decision_id='"'"'v350-deploy-smoke-decision'"'"'"')"
[[ "$alt_count" == "2" && "$crit_count" == "2" && "$asm_count" == "1" ]] || fail "Canvas normalized table counts invalid: alternatives=$alt_count criteria=$crit_count assumptions=$asm_count"
pass "Canvas alternatives/criteria/assumptions normalized into PostgreSQL"
docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "DELETE FROM decisions WHERE id='"'"'v350-deploy-smoke-decision'"'"'; DELETE FROM decision_projects WHERE id='"'"'v350-deploy-smoke-project'"'"';"' >/dev/null

echo "=== PRESERVED MODULE CONTRACTS ==="
mods="$(curl -fsS "http://127.0.0.1:${PORT}/decision-modules")"
python3 - "$mods" <<'PY'
import json,sys
r=json.loads(sys.argv[1])['registry']; ids={m['module_id'] for m in r['modules']}
assert r['module_count']==4 and ids=={'canvas','finance','narrative-risk','global-impact'},r
canvas=next(m for m in r['modules'] if m['module_id']=='canvas')
finance=next(m for m in r['modules'] if m['module_id']=='finance')
assert canvas['status']=='python-domain-authoritative' and canvas['storage_authority']=='python-postgresql',canvas
assert finance['providers']['compute_authority']=='workbench' and finance['status']=='foundation',finance
print('PASS: Canvas migrated; Finance/Narrative Risk/Global Impact remain staged for later domain migrations')
PY

echo "=== PUBLIC CADDY CHECK ==="
public="$(curl -fsS "$PUBLIC_URL/health")"
python3 - "$public" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x['persistence']
assert x['version']=='3.5.0' and x['build_fingerprint']=='scds-v3.5.0-canvas-python-domain-migration',x
assert x['canvas_domain_schema']=='scds-canvas-domain/1.0',x
assert p['connected'] and p['schema_current'] and p['authority']=='python-postgresql',p
assert p['write_enabled'] is True and p['authority_ready'] is True,p
print('PASS: public Decision Studio API returns v3.5.0 with authoritative Canvas domain')
PY
curl -fsS "$PUBLIC_URL/canvas/contract" | python3 -m json.tool

echo "=== FINAL CONTAINERS ==="
docker ps --filter "name=sc-decision-studio" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v3.5.0 deployed with Canvas Python domain authority"
echo "Backup: $backup"
echo "Persistence credentials: $PERSIST_ENV (mode 600; do not commit)"
