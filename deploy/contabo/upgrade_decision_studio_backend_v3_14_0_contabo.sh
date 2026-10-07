#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="3.14.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v3.14.0.zip}"
ROOT="${SCDS_ROOT:-/opt/sustainable-catalyst/decision-studio}"
LIVE_BACKEND="$ROOT/backend"
COMPOSE="$ROOT/compose.yml"
PERSIST_ENV="$ROOT/.env.persistence-v330"
SERVICE="${SCDS_COMPOSE_SERVICE:-decision-studio}"
DB_CONTAINER="${SCDS_DB_CONTAINER:-sc-decision-studio-postgres}"
CONTAINER="${SCDS_CONTAINER:-sc-decision-studio}"
PORT="${SCDS_PORT:-8089}"
PUBLIC_URL="${SCDS_PUBLIC_URL:-https://decision-studio-api.sustainablecatalyst.com}"
BACKUP_ROOT="${SCDS_BACKUP_ROOT:-/opt/sustainable-catalyst/backups}"
REVISION="0002_v3130_collaboration"
TMP="$(mktemp -d /tmp/sc-decision-studio-v3140.XXXXXX)"
SMOKE_PROJECT=""; SMOKE_DECISION=""; SMOKE_ROOM=""
fail(){ echo "ERROR: $*" >&2; exit 1; }
pass(){ echo "PASS: $*"; }
cleanup_smoke(){
  if [[ -n "$SMOKE_DECISION" ]] && docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
    docker exec "$DB_CONTAINER" sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -v ON_ERROR_STOP=1 -c \"DELETE FROM decision_room_events WHERE decision_id='${SMOKE_DECISION}'; DELETE FROM decision_room_share_grants WHERE room_id IN (SELECT id FROM decision_rooms WHERE decision_id='${SMOKE_DECISION}'); DELETE FROM decision_room_change_requests WHERE room_id IN (SELECT id FROM decision_rooms WHERE decision_id='${SMOKE_DECISION}'); DELETE FROM decision_room_comments WHERE room_id IN (SELECT id FROM decision_rooms WHERE decision_id='${SMOKE_DECISION}'); DELETE FROM decision_room_members WHERE room_id IN (SELECT id FROM decision_rooms WHERE decision_id='${SMOKE_DECISION}'); DELETE FROM snapshots WHERE decision_id='${SMOKE_DECISION}' AND snapshot_type='decision-room'; DELETE FROM decision_rooms WHERE decision_id='${SMOKE_DECISION}'; DELETE FROM decision_events WHERE decision_id='${SMOKE_DECISION}'; DELETE FROM decisions WHERE id='${SMOKE_DECISION}'; DELETE FROM decision_projects WHERE id='${SMOKE_PROJECT}';\"" >/dev/null 2>&1 || true
  fi
}
cleanup(){ cleanup_smoke; rm -rf "$TMP"; }
trap cleanup EXIT

[[ -f "$ARCHIVE" ]] || fail "backend archive not found: $ARCHIVE"
[[ -d "$ROOT" && -f "$COMPOSE" && -f "$PERSIST_ENV" ]] || fail "Decision Studio runtime root/compose/persistence env missing"
for c in docker python3 unzip rsync curl tar gzip openssl; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
mkdir -p "$BACKUP_ROOT"
unzip -q "$ARCHIVE" -d "$TMP/archive"
SRC="$(find "$TMP/archive" -type f -path '*/backend/app/main.py' -print -quit | sed 's#/app/main.py$##')"
COMPOSE_TEMPLATE="$(find "$TMP/archive" -type f -name 'compose.v3.14.0.yml' -print -quit)"
[[ -n "$SRC" && -n "$COMPOSE_TEMPLATE" ]] || fail "could not locate v3.14 backend/compose payload"
for required in app/main.py app/global_auth.py app/api/router.py app/api/routes/auth.py app/api/routes/decision_rooms.py app/decision_rooms.py app/services/decision_service.py app/persistence/database.py migrations/versions/0002_v3130_collaboration.py alembic.ini requirements.txt Dockerfile; do
  [[ -f "$SRC/$required" ]] || fail "v3.14 backend payload missing $required"
done
grep -q 'APP_VERSION = "3.14.0"' "$SRC/app/services/decision_service.py" || fail "payload is not v3.14.0"
grep -q 'scds-v3.14.0-global-authentication-authorization-integration' "$SRC/app/services/decision_service.py" || fail "v3.14 fingerprint missing"
grep -q 'GLOBAL_AUTH_SCHEMA = "scds-global-authentication-authorization/1.0"' "$SRC/app/global_auth.py" || fail "global auth schema missing"

for key in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD SCDS_DATABASE_URL SCDS_REPOSITORY_API_KEY; do grep -q "^${key}=" "$PERSIST_ENV" || fail "$PERSIST_ENV missing $key"; done
# Establish the shared Decision Studio relying-party secret only when none exists; never rotate it implicitly.
if ! grep -q '^SCDS_GLOBAL_AUTH_JWT_SECRET=' "$PERSIST_ENV"; then
  printf '\nSCDS_GLOBAL_AUTH_JWT_SECRET=%s\n' "$(openssl rand -hex 32)" >> "$PERSIST_ENV"
fi
grep -q '^SCDS_GLOBAL_AUTH_ISSUER=' "$PERSIST_ENV" || echo 'SCDS_GLOBAL_AUTH_ISSUER=sustainable-catalyst-auth' >> "$PERSIST_ENV"
grep -q '^SCDS_GLOBAL_AUTH_AUDIENCE=' "$PERSIST_ENV" || echo 'SCDS_GLOBAL_AUTH_AUDIENCE=decision-studio' >> "$PERSIST_ENV"
chmod 600 "$PERSIST_ENV"
set -a; source "$PERSIST_ENV"; set +a

psqlq(){ docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$1"; }
public_table_count(){ psqlq "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name <> 'alembic_version';"; }

echo "=== PRE-FLIGHT v3.13 BASELINE ==="
preflight="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
[[ -n "$preflight" ]] || fail "current backend health unavailable"
python3 - "$preflight" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{})
assert x.get('version') in {'3.13.0','3.14.0'},x
assert p.get('authority')=='python-postgresql' and p.get('authority_ready') is True,p
assert p.get('schema_revision')=='0002_v3130_collaboration' and p.get('table_count')==26,p
assert x.get('decision_room_python_persistence_schema')=='scds-decision-room-python-persistence/1.0',x
PY
pass "v3.13 room-persistence baseline (or safe v3.14 rerun) is healthy"

stamp="$(date +%Y%m%d-%H%M%S)"
CODE_BACKUP="$BACKUP_ROOT/decision-studio-before-v3.14.0-$stamp.tgz"
DB_BACKUP="$BACKUP_ROOT/decision-studio-db-before-v3.14.0-$stamp.sql.gz"
echo "=== BACKUP CODE + POSTGRESQL ==="
tar -czf "$CODE_BACKUP" -C "$ROOT" backend compose.yml .env.persistence-v330
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$DB_CONTAINER" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges | gzip -c > "$DB_BACKUP"
[[ -s "$DB_BACKUP" ]] || fail "PostgreSQL backup is empty"

mkdir -p "$TMP/env"
for envfile in .env .env.production; do [[ -f "$LIVE_BACKEND/$envfile" ]] && cp -a "$LIVE_BACKEND/$envfile" "$TMP/env/$envfile" || true; done
rsync -a --delete --exclude='.env' --exclude='.env.*' "$SRC/" "$LIVE_BACKEND/"
for envfile in .env .env.production; do [[ -f "$TMP/env/$envfile" ]] && cp -a "$TMP/env/$envfile" "$LIVE_BACKEND/$envfile" || true; done
cp "$COMPOSE_TEMPLATE" "$COMPOSE"
cd "$ROOT"
docker compose config --quiet

echo "=== VERIFY v3.13 SCHEMA IS PRESERVED ==="
docker compose up -d decision-studio-postgres
[[ "$(psqlq 'SELECT version_num FROM alembic_version LIMIT 1')" == "$REVISION" ]] || fail "unexpected pre-deploy schema revision"
[[ "$(public_table_count)" == "26" ]] || fail "expected 26 persistence tables before v3.14"

echo "=== BUILD v3.14.0 ==="
docker compose build "$SERVICE"
echo "=== ALEMBIC NO-OP / HEAD VERIFICATION ==="
docker compose run --rm "$SERVICE" alembic upgrade head
[[ "$(psqlq 'SELECT version_num FROM alembic_version LIMIT 1')" == "$REVISION" ]] || fail "v3.14 changed Alembic revision unexpectedly"
[[ "$(public_table_count)" == "26" ]] || fail "v3.14 changed persistence table count unexpectedly"
pass "v3.14 preserves $REVISION with 26 tables; no database migration"

echo "=== REFRESH MODULE REGISTRY ==="
docker compose run --rm "$SERVICE" python -m app.persistence.seed

echo "=== DEPLOY GLOBAL AUTHENTICATION & AUTHORIZATION INTEGRATION ==="
docker compose up -d "$SERVICE"
health=""
for _ in $(seq 1 45); do
  health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
  if [[ -n "$health" ]] && python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{}); a=x.get('release',{}).get('backend_architecture',{}); g=x.get('global_auth',{})
assert x.get('version')=='3.14.0',x
assert x.get('build_fingerprint')=='scds-v3.14.0-global-authentication-authorization-integration',x
assert x.get('global_auth_schema')=='scds-global-authentication-authorization/1.0',x
assert p.get('authority_ready') is True and p.get('schema_revision')=='0002_v3130_collaboration' and p.get('table_count')==26,p
assert a.get('route_count')==300 and a.get('router_registry_count')==24,a
assert a.get('global_authentication_authorization_integration') is True,a
assert g.get('user_authentication_ready') is True,g
PY
  then break; fi
  sleep 2
done
[[ -n "$health" ]] || { docker logs --tail=200 "$CONTAINER" >&2 || true; fail "backend did not answer /health"; }
pass "internal v3.14.0 health confirms Global Authentication & Authorization Integration"

echo "=== GLOBAL AUTH CONTRACT + BEARER SMOKE ==="
contract="$(curl -fsS "http://127.0.0.1:${PORT}/auth/contract")"
python3 - "$contract" <<'PY'
import json,sys
c=json.loads(sys.argv[1])['global_auth_contract']; p=c['principles']
assert c['schema']=='scds-global-authentication-authorization/1.0',c
assert c['authentication_authority']=='sustainable-catalyst-global-auth',c
assert c['primary_user_authentication']=='bearer-jwt-hs256',c
assert c['legacy_api_key_status']=='compatibility-only',c
assert p['decision_room_membership_is_enforced_for_user_principals'] is True,p
assert p['request_body_cannot_impersonate_authenticated_room_actor'] is True,p
assert c['schema_migration_required'] is False,c
PY
mint(){ python3 - "$1" "$2" "$3" <<'PY'
import base64,hashlib,hmac,json,os,sys,time
sub,scopes,inst=sys.argv[1:]
def b(x): return base64.urlsafe_b64encode(x).rstrip(b'=').decode()
now=int(time.time()); h={'alg':'HS256','typ':'JWT'}; p={'iss':os.environ.get('SCDS_GLOBAL_AUTH_ISSUER','sustainable-catalyst-auth'),'aud':os.environ.get('SCDS_GLOBAL_AUTH_AUDIENCE','decision-studio'),'sub':sub,'principal_type':'user','institution_id':inst,'scopes':scopes.split(','),'roles':['researcher'],'session_id':'deploy-smoke:'+sub,'iat':now,'exp':now+900}
h64=b(json.dumps(h,separators=(',',':'),sort_keys=True).encode()); p64=b(json.dumps(p,separators=(',',':'),sort_keys=True).encode()); sig=hmac.new(os.environ['SCDS_GLOBAL_AUTH_JWT_SECRET'].encode(),f'{h64}.{p64}'.encode(),hashlib.sha256).digest(); print(f'{h64}.{p64}.{b(sig)}')
PY
}
OWNER_TOKEN="$(mint 'user:v314-owner' 'rooms:read,rooms:write,auth:inspect' 'institution:v314-smoke')"
REVIEWER_TOKEN="$(mint 'user:v314-reviewer' 'rooms:read,rooms:write' 'institution:v314-smoke')"
OUTSIDER_TOKEN="$(mint 'user:v314-outsider' 'rooms:read,rooms:write' 'institution:v314-smoke')"
who="$(curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" "http://127.0.0.1:${PORT}/auth/whoami")"
python3 - "$who" <<'PY'
import json,sys
p=json.loads(sys.argv[1])['principal']; assert p['principal_id']=='user:v314-owner' and p['institution_id']=='institution:v314-smoke' and p['auth_method']=='global-bearer-jwt',p
PY
pass "globally issued bearer identity, institution, and scopes are accepted"

# An invalid bearer must never fall back to a simultaneously supplied legacy key.
code="$(curl -sS -o "$TMP/downgrade.json" -w '%{http_code}' -H 'Authorization: Bearer malformed.token.value' -H "X-SCDS-API-Key: $SCDS_REPOSITORY_API_KEY" "http://127.0.0.1:${PORT}/auth/whoami")"
[[ "$code" == "401" ]] || fail "invalid bearer downgrade resistance failed: HTTP $code"
pass "invalid bearer token cannot downgrade to legacy API-key authentication"

echo "=== DECISION ROOM MEMBERSHIP + ACTOR ANTI-SPOOF SMOKE ==="
SMOKE_PROJECT="proj-v3140-smoke-$stamp"; SMOKE_DECISION="dec-v3140-smoke-$stamp"
H="X-SCDS-API-Key: $SCDS_REPOSITORY_API_KEY"
curl -fsS -H "$H" -H 'content-type: application/json' -d "{\"project_id\":\"$SMOKE_PROJECT\",\"title\":\"v3.14 auth smoke\"}" "http://127.0.0.1:${PORT}/repository/projects" >/dev/null
curl -fsS -H "$H" -H 'content-type: application/json' -d "{\"decision_id\":\"$SMOKE_DECISION\",\"project_id\":\"$SMOKE_PROJECT\",\"decision_question\":\"v3.14 global auth smoke\"}" "http://127.0.0.1:${PORT}/repository/decisions" >/dev/null
room_json="$(curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" -H 'content-type: application/json' -d '{"title":"v3.14 Global Auth Room","owner_ref":"user:spoofed","actor_ref":"user:spoofed","actor_role":"observer"}' "http://127.0.0.1:${PORT}/decision-rooms/decisions/$SMOKE_DECISION")"
SMOKE_ROOM="$(python3 - "$room_json" <<'PY'
import json,sys
r=json.loads(sys.argv[1])['decision_room']; assert r['owner_ref']=='user:v314-owner',r; assert r['metadata']['institution_id']=='institution:v314-smoke',r; print(r['room_id'])
PY
)"
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" -H 'content-type: application/json' -d '{"user_ref":"user:v314-reviewer","name":"v3.14 Reviewer","role":"reviewer","actor_ref":"user:spoofed","actor_role":"observer"}' "http://127.0.0.1:${PORT}/decision-rooms/$SMOKE_ROOM/members" >/dev/null
comment="$(curl -fsS -H "Authorization: Bearer $REVIEWER_TOKEN" -H 'content-type: application/json' -d '{"author_ref":"user:v314-owner","author_role":"owner","content":"Authenticated reviewer smoke comment."}' "http://127.0.0.1:${PORT}/decision-rooms/$SMOKE_ROOM/comments")"
python3 - "$comment" <<'PY'
import json,sys
c=json.loads(sys.argv[1])['comment']; assert c['author_ref']=='user:v314-reviewer' and c['author_role']=='reviewer',c
PY
outcode="$(curl -sS -o "$TMP/outsider.json" -w '%{http_code}' -H "Authorization: Bearer $OUTSIDER_TOKEN" "http://127.0.0.1:${PORT}/decision-rooms/$SMOKE_ROOM")"
[[ "$outcode" == "403" ]] || fail "non-member Decision Room access should be 403, got $outcode"
access="$(curl -fsS -H "Authorization: Bearer $REVIEWER_TOKEN" "http://127.0.0.1:${PORT}/auth/decision-rooms/$SMOKE_ROOM/access")"
python3 - "$access" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); assert x['role']=='reviewer' and x['membership_enforced'] is True,x
PY
pass "Decision Room membership, institution binding, role authorization, and actor anti-spoofing succeeded"

echo "=== PRESERVED LAYERS ==="
curl -fsS "http://127.0.0.1:${PORT}/decision-rooms/contract" >/dev/null
curl -fsS "http://127.0.0.1:${PORT}/module-interoperability/contract" >/dev/null
curl -fsS "http://127.0.0.1:${PORT}/module-artifacts/contract" >/dev/null
curl -fsS "http://127.0.0.1:${PORT}/decision-composition/contract" >/dev/null
curl -fsS "http://127.0.0.1:${PORT}/decision-module-registry/readiness" >/dev/null
pass "v3.13 rooms, v3.12 shared evidence, v3.11 provenance, v3.10 composition, and v3.9 registry remain healthy"

echo "=== PUBLIC CADDY CHECK ==="
public_health="$(curl -fsS "$PUBLIC_URL/health")"; public_contract="$(curl -fsS "$PUBLIC_URL/auth/contract")"
python3 - "$public_health" "$public_contract" <<'PY'
import json,sys
h=json.loads(sys.argv[1]); c=json.loads(sys.argv[2])['global_auth_contract']; p=h['persistence']
assert h['version']=='3.14.0' and h['global_auth_schema']=='scds-global-authentication-authorization/1.0',h
assert p['schema_revision']=='0002_v3130_collaboration' and p['table_count']==26 and p['authority_ready'] is True,p
assert c['authentication_authority']=='sustainable-catalyst-global-auth' and c['legacy_api_key_status']=='compatibility-only',c
PY
pass "public Decision Studio API returns v3.14.0 with Global Authentication & Authorization Integration"

echo "=== CLEAN SYNTHETIC RECORDS ==="; cleanup_smoke; SMOKE_DECISION=""; SMOKE_PROJECT=""; SMOKE_ROOM=""
echo "=== FINAL CONTAINERS ==="; docker ps --filter name=sc-decision-studio --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v3.14.0 deployed with Global Authentication & Authorization Integration"
echo "Code backup: $CODE_BACKUP"
echo "Database backup: $DB_BACKUP"
echo "Global auth secret: stored in $PERSIST_ENV (mode 600; do not commit)"
