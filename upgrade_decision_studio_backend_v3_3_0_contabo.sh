#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="3.3.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v3.3.0.zip}"
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
TMP="$(mktemp -d /tmp/sc-decision-studio-v330.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }
pass(){ echo "PASS: $*"; }
[[ -f "$ARCHIVE" ]] || fail "backend archive not found: $ARCHIVE"
[[ -d "$ROOT" && -f "$COMPOSE" ]] || fail "Decision Studio runtime root/compose missing: $ROOT"
for c in docker python3 unzip rsync curl tar; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
mkdir -p "$BACKUP_ROOT"
unzip -q "$ARCHIVE" -d "$TMP/archive"
SRC="$(find "$TMP/archive" -type f -path '*/backend/app/main.py' -print -quit | sed 's#/app/main.py$##')"
COMPOSE_TEMPLATE="$(find "$TMP/archive" -type f -name 'compose.v3.3.0.yml' -print -quit)"
[[ -n "$SRC" && -n "$COMPOSE_TEMPLATE" ]] || fail "could not locate v3.3 backend/compose payload"
for required in app/main.py app/api/router.py app/services/decision_service.py app/persistence/database.py app/persistence/models.py app/persistence/repository.py app/persistence/seed.py migrations/env.py migrations/versions/0001_v330_postgresql_persistence_foundation.py alembic.ini requirements.txt Dockerfile; do
  [[ -f "$SRC/$required" ]] || fail "v3.3.0 backend payload missing $required"
done
grep -q 'APP_VERSION = "3.3.0"' "$SRC/app/services/decision_service.py" || fail "payload is not Decision Studio v3.3.0"
grep -q 'scds-v3.3.0-postgresql-persistence-foundation' "$SRC/app/services/decision_service.py" || fail "v3.3.0 fingerprint missing"
grep -q '0001_v330_postgresql_persistence_foundation' "$SRC/app/persistence/database.py" || fail "schema revision missing"
grep -q 'non-authoritative-foundation' "$SRC/app/persistence/database.py" || fail "authority boundary missing"
grep -q 'postgres:16-alpine' "$COMPOSE_TEMPLATE" || fail "PostgreSQL service missing from compose template"

echo "=== PRE-FLIGHT ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' || true
curl -fsS "http://127.0.0.1:${PORT}/health" | python3 -m json.tool || true
stamp="$(date +%Y%m%d-%H%M%S)"
backup="$BACKUP_ROOT/decision-studio-before-v3.3.0-$stamp.tgz"
echo "=== BACKUP ==="
items=(backend compose.yml)
[[ -f "$PERSIST_ENV" ]] && items+=(.env.persistence-v330)
tar -czf "$backup" -C "$ROOT" "${items[@]}"
echo "$backup"

# Preserve existing backend env files.
mkdir -p "$TMP/env"
for envfile in .env .env.production; do [[ -f "$LIVE_BACKEND/$envfile" ]] && cp -a "$LIVE_BACKEND/$envfile" "$TMP/env/$envfile"; done

# Generate persistent PostgreSQL credentials once. The file is never packaged or committed.
if [[ ! -f "$PERSIST_ENV" ]]; then
  PASSWORD="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"
  cat > "$PERSIST_ENV" <<EOF
POSTGRES_DB=decision_studio
POSTGRES_USER=decision_studio
POSTGRES_PASSWORD=$PASSWORD
SCDS_DATABASE_URL=postgresql+psycopg://decision_studio:$PASSWORD@decision-studio-postgres:5432/decision_studio
EOF
  chmod 600 "$PERSIST_ENV"
fi
for key in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD SCDS_DATABASE_URL; do grep -q "^${key}=" "$PERSIST_ENV" || fail "$PERSIST_ENV missing $key"; done

# Promote backend and v3.3 compose definition. Existing running v3.2 container remains untouched until final recreate.
rsync -a --delete --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='*.pyc' --exclude='.env' --exclude='.env.*' "$SRC/" "$LIVE_BACKEND/"
for envfile in .env .env.production; do [[ -f "$TMP/env/$envfile" ]] && cp -a "$TMP/env/$envfile" "$LIVE_BACKEND/$envfile"; done
cp "$COMPOSE_TEMPLATE" "$COMPOSE"
cd "$ROOT"
docker compose config --quiet

echo "=== START POSTGRESQL 16 ==="
docker compose up -d "$DB_SERVICE"
for _ in $(seq 1 60); do
  if docker exec "$DB_CONTAINER" sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then break; fi
  sleep 2
done
docker exec "$DB_CONTAINER" sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1 || fail "PostgreSQL did not become ready"

echo "=== BUILD v3.3.0 BACKEND ==="
docker compose build "$SERVICE"

echo "=== ALEMBIC MIGRATION ==="
docker compose run --rm "$SERVICE" alembic upgrade head

echo "=== SEED MODULE REGISTRY ==="
docker compose run --rm "$SERVICE" python -m app.persistence.seed

echo "=== DATABASE CERTIFICATION ==="
revision="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version LIMIT 1"')"
[[ "$revision" == "0001_v330_postgresql_persistence_foundation" ]] || fail "unexpected Alembic revision: $revision"
table_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema='"'"'public'"'"' AND table_type='"'"'BASE TABLE'"'"' AND table_name <> '"'"'alembic_version'"'"'"')"
[[ "$table_count" == "20" ]] || fail "expected 20 persistence tables, got $table_count"
module_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM decision_modules"')"
[[ "$module_count" == "4" ]] || fail "expected four seeded decision modules, got $module_count"
pass "PostgreSQL revision, 20-table schema, and four module seeds verified"

echo "=== DEPLOY BACKEND ==="
docker compose up -d --force-recreate "$SERVICE"
health=""
for _ in $(seq 1 60); do
  if health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null)"; then
    if python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]);p=x.get('persistence',{});r=x.get('release',{});a=r.get('backend_architecture',{})
assert x.get('ok') is True and x.get('ready') is True
assert x.get('version')=='3.3.0'
assert x.get('build_fingerprint')=='scds-v3.3.0-postgresql-persistence-foundation'
assert x.get('source_commit')=='release-v3.3.0'
assert p.get('connected') is True and p.get('schema_current') is True
assert p.get('schema_revision')=='0001_v330_postgresql_persistence_foundation'
assert p.get('authority')=='non-authoritative-foundation'
assert p.get('write_enabled') is False
assert a.get('database_migration') is True
assert a.get('postgresql_live_authority') is False
assert a.get('wordpress_authority_change') is False
PY
    then break; fi
  fi
  sleep 2
done
[[ -n "$health" ]] || { docker logs --tail=200 "$CONTAINER" >&2 || true; fail "backend did not answer /health"; }
python3 - "$health" <<'PY'
import json,sys
x=json.loads(sys.argv[1]);p=x['persistence'];a=x['release']['backend_architecture']
assert x['version']=='3.3.0',x
assert p['connected'] and p['schema_current'],p
assert p['table_count']==20 and p['authority']=='non-authoritative-foundation',p
assert p['write_enabled'] is False,p
assert a['route_count']==185 and a['router_registry_count']==13,a
assert a['database_migration'] is True and a['postgresql_live_authority'] is False,a
assert a['wordpress_authority_change'] is False,a
print('PASS: internal v3.3.0 health verifies PostgreSQL foundation without authority cutover')
PY

echo "=== PERSISTENCE API SMOKE ==="
status="$(curl -fsS "http://127.0.0.1:${PORT}/persistence/status")"
python3 - "$status" <<'PY'
import json,sys
x=json.loads(sys.argv[1]);p=x['persistence']
assert x['ok'] is True and x['version']=='3.3.0',x
assert p['connected'] is True and p['schema_current'] is True,p
assert p['schema_revision']=='0001_v330_postgresql_persistence_foundation',p
assert p['authority']=='non-authoritative-foundation' and p['write_enabled'] is False,p
print('PASS: persistence status is live and non-authoritative')
PY
contract="$(curl -fsS "http://127.0.0.1:${PORT}/persistence/contract")"
python3 - "$contract" <<'PY'
import json,sys
c=json.loads(sys.argv[1])['persistence_contract'];p=c['principles']
assert c['authority']=='non-authoritative-foundation',c
assert p['postgresql_is_live_authority'] is False and p['v3_4_authority_cutover_required'] is True,p
assert p['final_decision_authority']=='human-governed',p
print('PASS: v3.4 authority-cutover boundary preserved')
PY

echo "=== PRESERVED v3.2 DECISION KERNEL ==="
mods="$(curl -fsS "http://127.0.0.1:${PORT}/decision-modules")"
python3 - "$mods" <<'PY'
import json,sys
r=json.loads(sys.argv[1])['registry'];ids={m['module_id'] for m in r['modules']}
assert r['module_count']==4 and ids=={'canvas','finance','narrative-risk','global-impact'},r
finance=next(m for m in r['modules'] if m['module_id']=='finance')
assert finance['providers']['compute_authority']=='workbench',finance
print('PASS: v3.2 Decision Kernel module contracts preserved')
PY

echo "=== PUBLIC CADDY CHECK ==="
public="$(curl -fsS "$PUBLIC_URL/health")"
python3 - "$public" <<'PY'
import json,sys
x=json.loads(sys.argv[1]);p=x['persistence']
assert x['version']=='3.3.0' and x['build_fingerprint']=='scds-v3.3.0-postgresql-persistence-foundation',x
assert p['connected'] and p['schema_current'] and p['authority']=='non-authoritative-foundation',p
print('PASS: public Decision Studio API returns v3.3.0 with healthy PostgreSQL foundation')
PY
curl -fsS "$PUBLIC_URL/persistence/status" | python3 -m json.tool

echo "=== FINAL CONTAINERS ==="
docker ps --filter "name=sc-decision-studio" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v3.3.0 deployed with PostgreSQL persistence foundation"
echo "Backup: $backup"
echo "Persistence credentials: $PERSIST_ENV (mode 600; do not commit)"
