#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="3.4.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v3.4.0.zip}"
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
TMP="$(mktemp -d /tmp/sc-decision-studio-v340.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }
pass(){ echo "PASS: $*"; }

[[ -f "$ARCHIVE" ]] || fail "backend archive not found: $ARCHIVE"
[[ -d "$ROOT" && -f "$COMPOSE" ]] || fail "Decision Studio runtime root/compose missing: $ROOT"
for c in docker python3 unzip rsync curl tar; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
mkdir -p "$BACKUP_ROOT"
unzip -q "$ARCHIVE" -d "$TMP/archive"
SRC="$(find "$TMP/archive" -type f -path '*/backend/app/main.py' -print -quit | sed 's#/app/main.py$##')"
COMPOSE_TEMPLATE="$(find "$TMP/archive" -type f -name 'compose.v3.4.0.yml' -print -quit)"
[[ -n "$SRC" && -n "$COMPOSE_TEMPLATE" ]] || fail "could not locate v3.4 backend/compose payload"
for required in app/main.py app/api/router.py app/api/routes/repository.py app/services/decision_service.py app/persistence/database.py app/persistence/models.py app/persistence/contracts.py app/persistence/repository.py app/persistence/seed.py migrations/env.py migrations/versions/0001_v330_pg_foundation.py alembic.ini requirements.txt Dockerfile; do
  [[ -f "$SRC/$required" ]] || fail "v3.4 backend payload missing $required"
done
grep -q 'APP_VERSION = "3.4.0"' "$SRC/app/services/decision_service.py" || fail "payload is not Decision Studio v3.4.0"
grep -q 'scds-v3.4.0-python-decision-repository-object-persistence' "$SRC/app/services/decision_service.py" || fail "v3.4 fingerprint missing"
grep -q 'PERSISTENCE_AUTHORITY = "python-postgresql"' "$SRC/app/persistence/database.py" || fail "authoritative persistence boundary missing"
grep -q 'scds-python-decision-repository/1.0' "$SRC/app/persistence/contracts.py" || fail "repository schema missing"
grep -q 'SCDS_PERSISTENCE_WRITE_ENABLED: "true"' "$COMPOSE_TEMPLATE" || fail "v3.4 compose does not enable repository writes"

echo "=== PRE-FLIGHT ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' || true
curl -fsS "http://127.0.0.1:${PORT}/health" | python3 -m json.tool || true
[[ -f "$PERSIST_ENV" ]] || fail "v3.3 persistence credential file missing: $PERSIST_ENV"
for key in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD SCDS_DATABASE_URL; do grep -q "^${key}=" "$PERSIST_ENV" || fail "$PERSIST_ENV missing $key"; done
if ! grep -q '^SCDS_REPOSITORY_API_KEY=' "$PERSIST_ENV"; then
  REPOSITORY_KEY="$(python3 - <<'PYKEY'
import secrets
print(secrets.token_hex(32))
PYKEY
)"
  printf '\nSCDS_REPOSITORY_API_KEY=%s\n' "$REPOSITORY_KEY" >> "$PERSIST_ENV"
fi
chmod 600 "$PERSIST_ENV"
REPO_API_KEY="$(grep '^SCDS_REPOSITORY_API_KEY=' "$PERSIST_ENV" | tail -1 | cut -d= -f2-)"
[[ -n "$REPO_API_KEY" ]] || fail "repository API key is empty"

stamp="$(date +%Y%m%d-%H%M%S)"
backup="$BACKUP_ROOT/decision-studio-before-v3.4.0-$stamp.tgz"
echo "=== BACKUP ==="
tar -czf "$backup" -C "$ROOT" backend compose.yml .env.persistence-v330
echo "$backup"

mkdir -p "$TMP/env"
for envfile in .env .env.production; do [[ -f "$LIVE_BACKEND/$envfile" ]] && cp -a "$LIVE_BACKEND/$envfile" "$TMP/env/$envfile"; done

# Promote backend and v3.4 compose. The current v3.3.1 container remains running until final recreate.
rsync -a --delete --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='*.pyc' --exclude='.env' --exclude='.env.*' "$SRC/" "$LIVE_BACKEND/"
for envfile in .env .env.production; do [[ -f "$TMP/env/$envfile" ]] && cp -a "$TMP/env/$envfile" "$LIVE_BACKEND/$envfile"; done
cp "$COMPOSE_TEMPLATE" "$COMPOSE"
cd "$ROOT"
docker compose config --quiet

echo "=== VERIFY POSTGRESQL FOUNDATION ==="
docker compose up -d "$DB_SERVICE"
for _ in $(seq 1 60); do
  if docker exec "$DB_CONTAINER" sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then break; fi
  sleep 2
done
docker exec "$DB_CONTAINER" sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1 || fail "PostgreSQL did not become ready"
current_revision="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version LIMIT 1"' || true)"
[[ "$current_revision" == "$REVISION" ]] || fail "v3.4 requires certified v3.3.1 revision $REVISION; found ${current_revision:-<none>}"
table_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema='"'"'public'"'"' AND table_type='"'"'BASE TABLE'"'"' AND table_name <> '"'"'alembic_version'"'"'"')"
[[ "$table_count" == "20" ]] || fail "expected 20 persistence tables, got $table_count"
module_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM decision_modules"')"
[[ "$module_count" == "4" ]] || fail "expected four seeded decision modules, got $module_count"
pass "certified v3.3.1 PostgreSQL foundation is current"

echo "=== BUILD v3.4.0 BACKEND ==="
docker compose build "$SERVICE"

echo "=== ALEMBIC NO-OP / HEAD VERIFICATION ==="
docker compose run --rm "$SERVICE" alembic upgrade head
revision="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version LIMIT 1"')"
[[ "$revision" == "$REVISION" ]] || fail "schema revision changed unexpectedly: $revision"

echo "=== REFRESH MODULE REGISTRY ==="
docker compose run --rm "$SERVICE" python -m app.persistence.seed

echo "=== DEPLOY AUTHORITATIVE REPOSITORY ==="
docker compose up -d --force-recreate "$SERVICE"
health=""
for _ in $(seq 1 60); do
  if health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null)"; then
    if python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{}); a=x.get('release',{}).get('backend_architecture',{})
assert x.get('ok') is True and x.get('ready') is True
assert x.get('version')=='3.4.0'
assert x.get('build_fingerprint')=='scds-v3.4.0-python-decision-repository-object-persistence'
assert x.get('source_commit')=='release-v3.4.0'
assert x.get('repository_schema')=='scds-python-decision-repository/1.0'
assert p.get('connected') is True and p.get('schema_current') is True
assert p.get('schema_revision')=='0001_v330_pg_foundation'
assert p.get('authority')=='python-postgresql'
assert p.get('write_enabled') is True and p.get('authority_ready') is True
assert a.get('database_migration') is False
assert a.get('repository_authority_migration') is True
assert a.get('postgresql_live_authority') is True
PY
    then break; fi
  fi
  sleep 2
done
[[ -n "$health" ]] || { docker logs --tail=200 "$CONTAINER" >&2 || true; fail "backend did not answer /health"; }
python3 - "$health" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x['persistence']; a=x['release']['backend_architecture']
assert x['version']=='3.4.0',x
assert p['connected'] and p['schema_current'] and p['authority_ready'],p
assert p['table_count']==20 and p['authority']=='python-postgresql',p
assert p['write_enabled'] is True,p
assert a['route_count']==198 and a['router_registry_count']==14,a
assert a['database_migration'] is False and a['repository_authority_migration'] is True,a
assert a['postgresql_live_authority'] is True,a
print('PASS: internal v3.4.0 health confirms authoritative Python/PostgreSQL repository')
PY

echo "=== REPOSITORY AUTHORITY SMOKE ==="
authority="$(curl -fsS "http://127.0.0.1:${PORT}/repository/authority")"
python3 - "$authority" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); r=x['repository']; p=x['persistence']
assert x['ok'] is True and x['version']=='3.4.0',x
assert r['schema']=='scds-python-decision-repository/1.0',r
assert r['storage_authority']=='python-postgresql' and r['live_write_authority'] is True,r
assert r['final_decision_authority']=='human-governed',r
assert p['authority_ready'] is True and p['write_enabled'] is True,p
print('PASS: repository authority contract is live')
PY

echo "=== AUTHORITATIVE WRITE/READ SMOKE ==="
# Clean stale smoke rows from an interrupted prior attempt.
docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "DELETE FROM decisions WHERE id='"'"'v340-deploy-smoke-decision'"'"'; DELETE FROM decision_projects WHERE id='"'"'v340-deploy-smoke-project'"'"';"' >/dev/null
project="$(curl -fsS -X POST "http://127.0.0.1:${PORT}/repository/projects" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"project_id":"v340-deploy-smoke-project","title":"v3.4 repository deployment smoke"}')"
decision="$(curl -fsS -X POST "http://127.0.0.1:${PORT}/repository/decisions" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"decision_id":"v340-deploy-smoke-decision","project_id":"v340-deploy-smoke-project","decision_question":"Does authoritative repository persistence work?"}')"
object="$(curl -fsS -X PUT "http://127.0.0.1:${PORT}/repository/decisions/v340-deploy-smoke-decision/object" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"payload":{"schema":"scds-decision-object/1.0","decision_id":"v340-deploy-smoke-decision","status":"draft","question":"Does authoritative repository persistence work?","alternatives":[],"criteria":[]},"provenance_ref":"deploy:v3.4.0"}')"
readback="$(curl -fsS "http://127.0.0.1:${PORT}/repository/decisions/v340-deploy-smoke-decision/object" -H "X-SCDS-API-Key: $REPO_API_KEY")"
python3 - "$project" "$decision" "$object" "$readback" <<'PY'
import json,sys
p,d,o,r=map(json.loads,sys.argv[1:])
assert p['project']['id']=='v340-deploy-smoke-project'
assert d['decision']['id']=='v340-deploy-smoke-decision'
assert d['decision']['final_decision_authority']=='human-governed'
assert o['decision_object']['payload']['decision_id']=='v340-deploy-smoke-decision'
assert r['decision_object']['payload']==o['decision_object']['payload']
print('PASS: authoritative repository write/read round trip succeeded')
PY
# Remove only synthetic deployment smoke data; cascades remove object/events.
docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "DELETE FROM decisions WHERE id='"'"'v340-deploy-smoke-decision'"'"'; DELETE FROM decision_projects WHERE id='"'"'v340-deploy-smoke-project'"'"';"' >/dev/null

echo "=== PRESERVED DECISION KERNEL / MODULE CONTRACTS ==="
mods="$(curl -fsS "http://127.0.0.1:${PORT}/decision-modules")"
python3 - "$mods" <<'PY'
import json,sys
r=json.loads(sys.argv[1])['registry']; ids={m['module_id'] for m in r['modules']}
assert r['module_count']==4 and ids=={'canvas','finance','narrative-risk','global-impact'},r
finance=next(m for m in r['modules'] if m['module_id']=='finance')
assert finance['providers']['compute_authority']=='workbench',finance
print('PASS: four v3.2 module contracts preserved; Finance compute authority remains Workbench')
PY

echo "=== PUBLIC CADDY CHECK ==="
public="$(curl -fsS "$PUBLIC_URL/health")"
python3 - "$public" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x['persistence']
assert x['version']=='3.4.0' and x['build_fingerprint']=='scds-v3.4.0-python-decision-repository-object-persistence',x
assert x['repository_schema']=='scds-python-decision-repository/1.0',x
assert p['connected'] and p['schema_current'] and p['authority']=='python-postgresql',p
assert p['write_enabled'] is True and p['authority_ready'] is True,p
print('PASS: public Decision Studio API returns v3.4.0 with authoritative repository')
PY
curl -fsS "$PUBLIC_URL/repository/authority" | python3 -m json.tool

echo "=== FINAL CONTAINERS ==="
docker ps --filter "name=sc-decision-studio" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v3.4.0 deployed with Python/PostgreSQL repository authority"
echo "Backup: $backup"
echo "Persistence credentials: $PERSIST_ENV (mode 600; do not commit)"
