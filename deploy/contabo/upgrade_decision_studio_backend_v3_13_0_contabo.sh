#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="3.13.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v3.13.0.zip}"
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
PREVIOUS_REVISION="0001_v330_pg_foundation"
REVISION="0002_v3130_collaboration"
TMP="$(mktemp -d /tmp/sc-decision-studio-v3130.XXXXXX)"
SMOKE_DECISION=""
SMOKE_PROJECT=""
SMOKE_ROOM=""
CODE_BACKUP=""
DB_BACKUP=""

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
[[ -d "$ROOT" && -f "$COMPOSE" ]] || fail "Decision Studio runtime root/compose missing: $ROOT"
for c in docker python3 unzip rsync curl tar gzip; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
mkdir -p "$BACKUP_ROOT"
unzip -q "$ARCHIVE" -d "$TMP/archive"
SRC="$(find "$TMP/archive" -type f -path '*/backend/app/main.py' -print -quit | sed 's#/app/main.py$##')"
COMPOSE_TEMPLATE="$(find "$TMP/archive" -type f -name 'compose.v3.13.0.yml' -print -quit)"
[[ -n "$SRC" && -n "$COMPOSE_TEMPLATE" ]] || fail "could not locate v3.13 backend/compose payload"

for required in \
  app/main.py app/api/router.py app/api/routes/decision_rooms.py app/decision_rooms.py \
  app/api/routes/module_interoperability.py app/module_interoperability.py \
  app/api/routes/module_artifacts.py app/module_artifact_provenance.py \
  app/api/routes/composition.py app/cross_module_composition.py \
  app/api/routes/module_registry.py app/unified_module_registry.py \
  app/services/decision_service.py app/persistence/database.py app/persistence/models.py app/persistence/repository.py \
  migrations/env.py migrations/versions/0001_v330_pg_foundation.py migrations/versions/0002_v3130_collaboration.py \
  alembic.ini requirements.txt Dockerfile; do
  [[ -f "$SRC/$required" ]] || fail "v3.13 backend payload missing $required"
done

grep -q 'APP_VERSION = "3.13.0"' "$SRC/app/services/decision_service.py" || fail "payload is not v3.13.0"
grep -q 'scds-v3.13.0-collaboration-decision-room-python-persistence' "$SRC/app/services/decision_service.py" || fail "v3.13 fingerprint missing"
grep -q 'DECISION_ROOM_PERSISTENCE_SCHEMA = "scds-decision-room-python-persistence/1.0"' "$SRC/app/decision_rooms.py" || fail "decision-room persistence schema missing"
grep -q 'revision = "0002_v3130_collaboration"' "$SRC/migrations/versions/0002_v3130_collaboration.py" || fail "v3.13 Alembic revision missing"
grep -q 'down_revision = "0001_v330_pg_foundation"' "$SRC/migrations/versions/0002_v3130_collaboration.py" || fail "v3.13 migration chain invalid"

[[ -f "$PERSIST_ENV" ]] || fail "persistence credential file missing: $PERSIST_ENV"
for key in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD SCDS_DATABASE_URL SCDS_REPOSITORY_API_KEY; do grep -q "^${key}=" "$PERSIST_ENV" || fail "$PERSIST_ENV missing $key"; done
chmod 600 "$PERSIST_ENV"
set -a; source "$PERSIST_ENV"; set +a

psqlq(){
  local sql="$1"
  docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$DB_CONTAINER" \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$sql"
}

room_table_count(){
  psqlq "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('decision_rooms','decision_room_members','decision_room_comments','decision_room_change_requests','decision_room_share_grants','decision_room_events');"
}

public_table_count(){
  psqlq "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name <> 'alembic_version';"
}

echo "=== PRE-FLIGHT v3.12 BASELINE ==="
preflight="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
[[ -n "$preflight" ]] || fail "current backend health unavailable"
python3 - "$preflight" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{})
assert x.get('version') in {'3.12.0','3.13.0'}, x
assert p.get('authority')=='python-postgresql' and p.get('authority_ready') is True, p
if x.get('version')=='3.12.0':
    assert p.get('schema_revision')=='0001_v330_pg_foundation' and p.get('table_count')==20, p
    assert x.get('module_interoperability_schema')=='scds-module-interoperability/1.0', x
    assert x.get('shared_evidence_schema')=='scds-shared-evidence-reference/1.0', x
else:
    assert p.get('schema_revision')=='0002_v3130_collaboration' and p.get('table_count')==26, p
PY
pass "v3.12 interoperability/repository baseline (or safe v3.13 rerun) is healthy"

stamp="$(date +%Y%m%d-%H%M%S)"
CODE_BACKUP="$BACKUP_ROOT/decision-studio-before-v3.13.0-$stamp.tgz"
DB_BACKUP="$BACKUP_ROOT/decision-studio-db-before-v3.13.0-$stamp.sql.gz"
echo "=== BACKUP CODE + POSTGRESQL ==="
tar -czf "$CODE_BACKUP" -C "$ROOT" backend compose.yml .env.persistence-v330
# pg_dump runs inside the PostgreSQL container; only the compressed dump leaves the container.
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$DB_CONTAINER" \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges | gzip -c > "$DB_BACKUP"
[[ -s "$DB_BACKUP" ]] || fail "PostgreSQL backup is empty: $DB_BACKUP"
echo "$CODE_BACKUP"
echo "$DB_BACKUP"

mkdir -p "$TMP/env"
for envfile in .env .env.production; do [[ -f "$LIVE_BACKEND/$envfile" ]] && cp -a "$LIVE_BACKEND/$envfile" "$TMP/env/$envfile" || true; done
rsync -a --delete --exclude='.env' --exclude='.env.*' "$SRC/" "$LIVE_BACKEND/"
for envfile in .env .env.production; do [[ -f "$TMP/env/$envfile" ]] && cp -a "$TMP/env/$envfile" "$LIVE_BACKEND/$envfile" || true; done
cp "$COMPOSE_TEMPLATE" "$COMPOSE"
cd "$ROOT"
docker compose config --quiet

echo "=== VERIFY PRE-MIGRATION POSTGRESQL FOUNDATION ==="
docker compose up -d decision-studio-postgres
pre_rev="$(psqlq 'SELECT version_num FROM alembic_version LIMIT 1')"
pre_tables="$(public_table_count)"
if [[ "$pre_rev" == "$PREVIOUS_REVISION" ]]; then
  [[ "$pre_tables" == "20" ]] || fail "expected 20 pre-v3.13 persistence tables, found $pre_tables"
elif [[ "$pre_rev" == "$REVISION" ]]; then
  [[ "$pre_tables" == "26" ]] || fail "v3.13 revision exists but table count is $pre_tables, expected 26"
else
  fail "unexpected schema revision before v3.13 deployment: $pre_rev"
fi

echo "=== BUILD v3.13.0 ==="
docker compose build "$SERVICE"

echo "=== APPLY ALEMBIC v3.13 COLLABORATION MIGRATION ==="
docker compose run --rm "$SERVICE" alembic upgrade head
post_rev="$(psqlq 'SELECT version_num FROM alembic_version LIMIT 1')"
post_tables="$(public_table_count)"
rooms="$(room_table_count)"
[[ "$post_rev" == "$REVISION" ]] || fail "expected Alembic revision $REVISION, found $post_rev"
[[ "$post_tables" == "26" ]] || fail "expected 26 persistence tables after v3.13 migration, found $post_tables"
[[ "$rooms" == "6" ]] || fail "expected all 6 collaboration tables, found $rooms"
for table in decision_rooms decision_room_members decision_room_comments decision_room_change_requests decision_room_share_grants decision_room_events; do
  [[ "$(psqlq "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='${table}';")" == "1" ]] || fail "missing collaboration table: $table"
done
pass "Alembic upgraded to $REVISION with 26 tables and six collaboration tables"

echo "=== REFRESH MODULE REGISTRY ==="
docker compose run --rm "$SERVICE" python -m app.persistence.seed

echo "=== DEPLOY COLLABORATION & DECISION ROOM PYTHON PERSISTENCE ==="
docker compose up -d "$SERVICE"
health=""
for _ in $(seq 1 45); do
  health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
  if [[ -n "$health" ]] && python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{}); a=x.get('release',{}).get('backend_architecture',{})
assert x.get('version')=='3.13.0', x
assert x.get('build_fingerprint')=='scds-v3.13.0-collaboration-decision-room-python-persistence', x
assert x.get('decision_room_python_persistence_schema')=='scds-decision-room-python-persistence/1.0', x
assert x.get('decision_room_schema_v2')=='scds-collaborative-decision-room/2.0', x
assert x.get('decision_room_event_schema_v2')=='scds-collaboration-event/2.0', x
assert p.get('connected') and p.get('schema_current') and p.get('authority_ready'), p
assert p.get('schema_revision')=='0002_v3130_collaboration' and p.get('table_count')==26, p
assert a.get('route_count')==293 and a.get('router_registry_count')==23, a
assert a.get('collaboration_decision_room_python_persistence') is True, a
PY
  then break; fi
  sleep 2
done
[[ -n "$health" ]] || { docker logs --tail=200 "$CONTAINER" >&2 || true; fail "backend did not answer /health"; }
python3 - "$health" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{})
assert x.get('version')=='3.13.0', x
assert p.get('schema_revision')=='0002_v3130_collaboration' and p.get('table_count')==26 and p.get('authority_ready') is True, p
PY
pass "internal v3.13.0 health confirms Collaboration & Decision Room Python Persistence"

echo "=== DECISION ROOM CONTRACT SMOKE ==="
contract="$(curl -fsS "http://127.0.0.1:${PORT}/decision-rooms/contract")"
python3 - "$contract" <<'PY'
import json,sys
c=json.loads(sys.argv[1])['decision_room_contract']; p=c['principles']
assert c['schema']=='scds-collaborative-decision-room/2.0', c
assert c['event_schema']=='scds-collaboration-event/2.0', c
assert c['persistence_schema']=='scds-decision-room-python-persistence/1.0', c
assert c['storage_authority']=='python-postgresql', c
assert p['room_state_is_persisted_in_python_postgresql'] is True, p
assert p['legacy_wordpress_room_is_compatibility_only'] is True, p
assert p['share_token_plaintext_is_never_persisted'] is True, p
assert p['room_events_are_hash_chained'] is True, p
assert c['final_decision_authority']=='human-governed', c
PY
pass "decision-room contract preserves Python/PostgreSQL authority, token safety, event integrity, and human governance"

echo "=== AUTHORITATIVE ROOM PERSISTENCE SMOKE ==="
SMOKE_PROJECT="proj-v3130-smoke-$stamp"
SMOKE_DECISION="dec-v3130-smoke-$stamp"
H="x-scds-api-key: $SCDS_REPOSITORY_API_KEY"
curl -fsS -H "$H" -H 'content-type: application/json' \
  -d "{\"project_id\":\"$SMOKE_PROJECT\",\"title\":\"v3.13 decision-room smoke\"}" \
  "http://127.0.0.1:${PORT}/repository/projects" >/dev/null
curl -fsS -H "$H" -H 'content-type: application/json' \
  -d "{\"decision_id\":\"$SMOKE_DECISION\",\"project_id\":\"$SMOKE_PROJECT\",\"decision_question\":\"v3.13 collaboration persistence smoke\"}" \
  "http://127.0.0.1:${PORT}/repository/decisions" >/dev/null

room_json="$(curl -fsS -H "$H" -H 'content-type: application/json' \
  -d '{"title":"v3.13 Production Smoke Room","visibility":"private","status":"active","owner_ref":"smoke:owner","actor_ref":"smoke:owner","actor_role":"owner","metadata":{"purpose":"deployment-smoke"}}' \
  "http://127.0.0.1:${PORT}/decision-rooms/decisions/$SMOKE_DECISION")"
SMOKE_ROOM="$(python3 - "$room_json" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); r=x['decision_room']
assert r['canonical_persistence']=='python-postgresql' and r['final_decision_authority']=='human-governed', r
print(r['room_id'])
PY
)"
[[ -n "$SMOKE_ROOM" ]] || fail "decision room id missing"

member_json="$(curl -fsS -H "$H" -H 'content-type: application/json' \
  -d '{"member_id":"member-v3130-reviewer","user_ref":"smoke:reviewer","name":"v3.13 Reviewer","role":"reviewer","actor_ref":"smoke:owner","actor_role":"owner"}' \
  "http://127.0.0.1:${PORT}/decision-rooms/$SMOKE_ROOM/members")"
python3 - "$member_json" <<'PY'
import json,sys
m=json.loads(sys.argv[1])['member']; assert m['role']=='reviewer' and m['status']=='active',m
PY

comment_json="$(curl -fsS -H "$H" -H 'content-type: application/json' \
  -d '{"author_ref":"smoke:reviewer","author_role":"reviewer","target_type":"decision","content":"Reviewer smoke comment."}' \
  "http://127.0.0.1:${PORT}/decision-rooms/$SMOKE_ROOM/comments")"
python3 - "$comment_json" <<'PY'
import json,sys
c=json.loads(sys.argv[1])['comment']; assert c['author_role']=='reviewer' and c['status']=='open',c
PY

change_json="$(curl -fsS -H "$H" -H 'content-type: application/json' \
  -d '{"requested_by":"smoke:reviewer","requester_role":"reviewer","target_type":"decision","summary":"Please document the deployment smoke evidence.","packet_patch":{"smoke":true}}' \
  "http://127.0.0.1:${PORT}/decision-rooms/$SMOKE_ROOM/change-requests")"
python3 - "$change_json" <<'PY'
import json,sys
c=json.loads(sys.argv[1])['change_request']; assert c['requester_role']=='reviewer' and c['status']=='open',c
PY

snapshot_json="$(curl -fsS -H "$H" -H 'content-type: application/json' \
  -d '{"payload":{"smoke":true,"stage":"review"},"label":"v3.13 production smoke snapshot","actor_ref":"smoke:reviewer","actor_role":"reviewer"}' \
  "http://127.0.0.1:${PORT}/decision-rooms/$SMOKE_ROOM/snapshots")"
python3 - "$snapshot_json" <<'PY'
import json,sys
s=json.loads(sys.argv[1])['snapshot']; assert s['snapshot_type']=='decision-room' and len(s['content_sha256'])==64,s
PY

grant_json="$(curl -fsS -H "$H" -H 'content-type: application/json' \
  -d '{"member_id":"member-v3130-reviewer","role":"reviewer","actor_ref":"smoke:owner","actor_role":"owner","metadata":{"purpose":"deployment-smoke"}}' \
  "http://127.0.0.1:${PORT}/decision-rooms/$SMOKE_ROOM/share-grants")"
read -r GRANT_ID TOKEN TOKEN_SHA <<<"$(python3 - "$grant_json" <<'PY'
import hashlib,json,sys
x=json.loads(sys.argv[1]); g=x['share_grant']; token=x['share_token_once']
assert g['role']=='reviewer' and 'token_hash' not in g and token, x
print(g['grant_id'], token, hashlib.sha256(token.encode()).hexdigest())
PY
)"
[[ -n "$GRANT_ID" && -n "$TOKEN" && -n "$TOKEN_SHA" ]] || fail "share grant smoke failed"
stored_hash="$(psqlq "SELECT token_hash FROM decision_room_share_grants WHERE id='${GRANT_ID}';")"
[[ "$stored_hash" == "$TOKEN_SHA" ]] || fail "stored share-token SHA-256 does not match returned one-time token"
if psqlq "SELECT metadata_json::text FROM decision_room_share_grants WHERE id='${GRANT_ID}';" | grep -Fq "$TOKEN"; then
  fail "share-token plaintext leaked into persisted metadata"
fi

events_json="$(curl -fsS -H "$H" "http://127.0.0.1:${PORT}/decision-rooms/$SMOKE_ROOM/events")"
python3 - "$events_json" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); i=x['integrity']
assert i['ok'] is True and i['event_count'] >= 6 and len(i['head_hash'])==64,(i,x.get('events'))
PY

room_count="$(psqlq "SELECT count(*) FROM decision_rooms WHERE decision_id='${SMOKE_DECISION}';")"
member_count="$(psqlq "SELECT count(*) FROM decision_room_members WHERE room_id='${SMOKE_ROOM}';")"
comment_count="$(psqlq "SELECT count(*) FROM decision_room_comments WHERE room_id='${SMOKE_ROOM}';")"
change_count="$(psqlq "SELECT count(*) FROM decision_room_change_requests WHERE room_id='${SMOKE_ROOM}';")"
grant_count="$(psqlq "SELECT count(*) FROM decision_room_share_grants WHERE room_id='${SMOKE_ROOM}';")"
event_count="$(psqlq "SELECT count(*) FROM decision_room_events WHERE room_id='${SMOKE_ROOM}';")"
snapshot_count="$(psqlq "SELECT count(*) FROM snapshots WHERE decision_id='${SMOKE_DECISION}' AND snapshot_type='decision-room';")"
[[ "$room_count" == "1" ]] || fail "expected one canonical decision room, found $room_count"
[[ "$member_count" -ge 2 ]] || fail "expected owner + reviewer members, found $member_count"
[[ "$comment_count" == "1" && "$change_count" == "1" && "$grant_count" == "1" && "$snapshot_count" == "1" ]] || fail "room child persistence counts invalid"
[[ "$event_count" -ge 6 ]] || fail "expected at least six hash-chained room events, found $event_count"
pass "authoritative room/member/comment/change/snapshot/share/event persistence succeeded; share token stored only as SHA-256"

echo "=== LEGACY WORDPRESS COMPATIBILITY SURFACE ==="
legacy="$(curl -fsS "http://127.0.0.1:${PORT}/collaboration/template")"
python3 - "$legacy" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); room=x.get('room') or x.get('collaboration_room') or x
# The legacy route is preserved, but its projection must disclose Python/PostgreSQL as canonical.
assert room.get('canonical_persistence')=='python-postgresql', room
assert room.get('legacy_wordpress_projection')=='compatibility-preserved', room
PY
pass "legacy WordPress collaboration projection is preserved but no longer canonical"

echo "=== v3.12 + v3.11 + v3.10 + v3.9 PRESERVATION ==="
curl -fsS "http://127.0.0.1:${PORT}/module-interoperability/contract" >/dev/null
curl -fsS "http://127.0.0.1:${PORT}/module-artifacts/contract" >/dev/null
curl -fsS "http://127.0.0.1:${PORT}/decision-composition/contract" >/dev/null
readiness="$(curl -fsS "http://127.0.0.1:${PORT}/decision-module-registry/readiness")"
python3 - "$readiness" <<'PY'
import json,sys
r=json.loads(sys.argv[1])['readiness']; assert r['ready'] and r['all_modules_authoritative'] and r['module_count']==4,r
PY
pass "v3.12 shared evidence, v3.11 artifacts, v3.10 composition, and v3.9 registry remain healthy"

echo "=== PUBLIC CADDY CHECK ==="
public="$(curl -fsS "$PUBLIC_URL/health")"
python3 - "$public" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x['persistence']; a=x['release']['backend_architecture']
assert x['version']=='3.13.0',x
assert x['decision_room_python_persistence_schema']=='scds-decision-room-python-persistence/1.0',x
assert p['connected'] and p['schema_current'] and p['authority_ready'],p
assert p['schema_revision']=='0002_v3130_collaboration' and p['table_count']==26,p
assert a['collaboration_decision_room_python_persistence'] is True,a
PY
curl -fsS "$PUBLIC_URL/decision-rooms/contract" | python3 -m json.tool
pass "public Decision Studio API returns v3.13.0 with authoritative Collaboration & Decision Room Python Persistence"

echo "=== CLEAN SYNTHETIC ROOM RECORDS ==="
cleanup_smoke
SMOKE_DECISION=""; SMOKE_PROJECT=""; SMOKE_ROOM=""

echo "=== FINAL CONTAINERS ==="
docker ps --filter "name=sc-decision-studio" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v3.13.0 deployed with Collaboration & Decision Room Python Persistence"
echo "Code backup: $CODE_BACKUP"
echo "Database backup: $DB_BACKUP"
echo "Persistence credentials: $PERSIST_ENV (mode 600; do not commit)"
