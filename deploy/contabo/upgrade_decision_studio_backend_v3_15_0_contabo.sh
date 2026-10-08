#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="3.15.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v3.15.0.zip}"
ROOT="${SCDS_ROOT:-/opt/sustainable-catalyst/decision-studio}"
LIVE_BACKEND="$ROOT/backend"; COMPOSE="$ROOT/compose.yml"; PERSIST_ENV="$ROOT/.env.persistence-v330"
SERVICE="${SCDS_COMPOSE_SERVICE:-decision-studio}"; DB_CONTAINER="${SCDS_DB_CONTAINER:-sc-decision-studio-postgres}"; CONTAINER="${SCDS_CONTAINER:-sc-decision-studio}"
PORT="${SCDS_PORT:-8089}"; PUBLIC_URL="${SCDS_PUBLIC_URL:-https://decision-studio-api.sustainablecatalyst.com}"; BACKUP_ROOT="${SCDS_BACKUP_ROOT:-/opt/sustainable-catalyst/backups}"
PREV_REVISION="0002_v3130_collaboration"; REVISION="0003_v3150_event_ledger"
TMP="$(mktemp -d /tmp/sc-decision-studio-v3150.XXXXXX)"; SMOKE_PROJECT=""; SMOKE_DECISION=""
fail(){ echo "ERROR: $*" >&2; exit 1; }; pass(){ echo "PASS: $*"; }
wait_postgres(){ for _ in $(seq 1 60); do if docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER" && docker exec "$DB_CONTAINER" sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then return 0; fi; sleep 2; done; docker logs --tail=200 "$DB_CONTAINER" >&2 || true; fail "PostgreSQL did not become ready"; }
psqlq(){ wait_postgres; docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$1"; }
public_table_count(){ psqlq "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name <> 'alembic_version';"; }
cleanup_smoke(){
  if [[ -n "$SMOKE_DECISION" ]] && docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
    docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "BEGIN; SET LOCAL scds.audit_maintenance='on'; DELETE FROM decision_audit_events WHERE decision_id='${SMOKE_DECISION}'; DELETE FROM decision_events WHERE decision_id='${SMOKE_DECISION}'; DELETE FROM decisions WHERE id='${SMOKE_DECISION}'; DELETE FROM decision_projects WHERE id='${SMOKE_PROJECT}'; COMMIT;" >/dev/null 2>&1 || true
  fi
}
cleanup(){ cleanup_smoke; rm -rf "$TMP"; }; trap cleanup EXIT

[[ -f "$ARCHIVE" ]] || fail "backend archive not found: $ARCHIVE"; [[ -d "$ROOT" && -f "$COMPOSE" && -f "$PERSIST_ENV" ]] || fail "runtime root/compose/persistence env missing"
for c in docker python3 unzip rsync curl tar gzip; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
mkdir -p "$BACKUP_ROOT"; unzip -q "$ARCHIVE" -d "$TMP/archive"
SRC="$(find "$TMP/archive" -type f -path '*/backend/app/main.py' -print -quit | sed 's#/app/main.py$##')"; COMPOSE_TEMPLATE="$(find "$TMP/archive" -type f -name 'compose.v3.15.0.yml' -print -quit)"
[[ -n "$SRC" && -n "$COMPOSE_TEMPLATE" ]] || fail "could not locate v3.15 backend/compose payload"
for required in app/main.py app/audit_ledger.py app/global_auth.py app/api/router.py app/api/routes/audit_ledger.py app/services/decision_service.py app/persistence/database.py app/persistence/models.py migrations/versions/0003_v3150_event_ledger.py alembic.ini requirements.txt Dockerfile; do [[ -f "$SRC/$required" ]] || fail "v3.15 payload missing $required"; done
grep -q 'APP_VERSION = "3.15.0"' "$SRC/app/services/decision_service.py" || fail "payload is not v3.15.0"; grep -q 'scds-v3.15.0-decision-event-store-immutable-audit-ledger' "$SRC/app/services/decision_service.py" || fail "v3.15 fingerprint missing"
for key in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD SCDS_DATABASE_URL SCDS_REPOSITORY_API_KEY; do grep -q "^${key}=" "$PERSIST_ENV" || fail "$PERSIST_ENV missing $key"; done
chmod 600 "$PERSIST_ENV"; set -a; source "$PERSIST_ENV"; set +a

echo "=== PRE-FLIGHT v3.14 BASELINE ==="; preflight="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"; [[ -n "$preflight" ]] || fail "current backend health unavailable"
python3 - "$preflight" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{})
assert x.get('version') in {'3.14.0','3.15.0'},x
assert p.get('authority')=='python-postgresql' and p.get('authority_ready') is True,p
assert (p.get('schema_revision'),p.get('table_count')) in {('0002_v3130_collaboration',26),('0003_v3150_event_ledger',27)},p
assert x.get('global_auth_schema')=='scds-global-authentication-authorization/1.0',x
PY
pass "v3.14 global-auth baseline (or safe v3.15 rerun) is healthy"

stamp="$(date +%Y%m%d-%H%M%S)"; CODE_BACKUP="$BACKUP_ROOT/decision-studio-before-v3.15.0-$stamp.tgz"; DB_BACKUP="$BACKUP_ROOT/decision-studio-db-before-v3.15.0-$stamp.sql.gz"
echo "=== BACKUP CODE + POSTGRESQL ==="; wait_postgres; tar -czf "$CODE_BACKUP" -C "$ROOT" backend compose.yml .env.persistence-v330; docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$DB_CONTAINER" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges | gzip -c > "$DB_BACKUP"; [[ -s "$DB_BACKUP" ]] || fail "PostgreSQL backup is empty"

mkdir -p "$TMP/env"; for envfile in .env .env.production; do [[ -f "$LIVE_BACKEND/$envfile" ]] && cp -a "$LIVE_BACKEND/$envfile" "$TMP/env/$envfile" || true; done
rsync -a --delete --exclude='.env' --exclude='.env.*' "$SRC/" "$LIVE_BACKEND/"; for envfile in .env .env.production; do [[ -f "$TMP/env/$envfile" ]] && cp -a "$TMP/env/$envfile" "$LIVE_BACKEND/$envfile" || true; done
cp "$COMPOSE_TEMPLATE" "$COMPOSE"; cd "$ROOT"; docker compose config --quiet; docker compose up -d decision-studio-postgres; wait_postgres
pre_rev="$(psqlq 'SELECT version_num FROM alembic_version LIMIT 1')"; pre_tables="$(public_table_count)"; [[ "$pre_rev:$pre_tables" == "$PREV_REVISION:26" || "$pre_rev:$pre_tables" == "$REVISION:27" ]] || fail "unexpected pre-migration state $pre_rev / $pre_tables tables"

echo "=== BUILD v3.15.0 ==="; docker compose build "$SERVICE"
echo "=== APPLY ALEMBIC v3.15 EVENT LEDGER MIGRATION ==="; docker compose run --rm "$SERVICE" alembic upgrade head
[[ "$(psqlq 'SELECT version_num FROM alembic_version LIMIT 1')" == "$REVISION" ]] || fail "v3.15 migration revision mismatch"; [[ "$(public_table_count)" == "27" ]] || fail "expected 27 persistence tables after v3.15"
[[ "$(psqlq "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='decision_audit_events';")" == "1" ]] || fail "decision_audit_events table missing"
pass "Alembic upgraded to $REVISION with 27 tables and append-only audit ledger table"

echo "=== BACKFILL HISTORICAL DECISION EVENTS ==="; docker compose run --rm "$SERVICE" python -m app.audit_ledger backfill
pass "historical decision_events backfill completed idempotently"
echo "=== REFRESH MODULE REGISTRY ==="; docker compose run --rm "$SERVICE" python -m app.persistence.seed

echo "=== DEPLOY DECISION EVENT STORE & IMMUTABLE AUDIT LEDGER ==="; docker compose up -d "$SERVICE"
health=""; for _ in $(seq 1 45); do health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"; if [[ -n "$health" ]] && python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{}); a=x.get('release',{}).get('backend_architecture',{})
assert x.get('version')=='3.15.0',x
assert x.get('build_fingerprint')=='scds-v3.15.0-decision-event-store-immutable-audit-ledger',x
assert x.get('immutable_audit_ledger_schema')=='scds-immutable-audit-ledger/1.0',x
assert p.get('authority_ready') is True and p.get('schema_revision')=='0003_v3150_event_ledger' and p.get('table_count')==27,p
assert a.get('route_count')==308 and a.get('router_registry_count')==25,a
assert a.get('decision_event_store_immutable_audit_ledger') is True,a
PY
then break; fi; sleep 2; done
[[ -n "$health" ]] || { docker logs --tail=200 "$CONTAINER" >&2 || true; fail "backend did not answer /health"; }; pass "internal v3.15.0 health confirms Decision Event Store & Immutable Audit Ledger"

echo "=== AUDIT CONTRACT SMOKE ==="; contract="$(curl -fsS "http://127.0.0.1:${PORT}/audit-ledger/contract")"; python3 - "$contract" <<'PY'
import json,sys
c=json.loads(sys.argv[1])['audit_ledger_contract']; p=c['principles']
assert c['schema']=='scds-immutable-audit-ledger/1.0' and c['migration_revision']=='0003_v3150_event_ledger',c
assert p['append_only'] and p['database_mutation_guard'] and p['sha256_hash_chain'] and p['replay_does_not_reexecute_domain_mutations'],p
assert c['final_decision_authority']=='human-governed',c
PY
pass "audit-ledger contract preserves append-only integrity and human governance boundaries"

echo "=== AUTHORITATIVE LEDGER SMOKE ==="; SMOKE_PROJECT="proj-v3150-smoke-$stamp"; SMOKE_DECISION="dec-v3150-smoke-$stamp"; H="X-SCDS-API-Key: $SCDS_REPOSITORY_API_KEY"
curl -fsS -H "$H" -H 'content-type: application/json' -d "{\"project_id\":\"$SMOKE_PROJECT\",\"title\":\"v3.15 ledger smoke\"}" "http://127.0.0.1:${PORT}/repository/projects" >/dev/null
curl -fsS -H "$H" -H 'content-type: application/json' -d "{\"decision_id\":\"$SMOKE_DECISION\",\"project_id\":\"$SMOKE_PROJECT\",\"decision_question\":\"v3.15 audit ledger smoke\"}" "http://127.0.0.1:${PORT}/repository/decisions" >/dev/null
curl -fsS -X PATCH -H "$H" -H 'content-type: application/json' -d '{"lifecycle_state":"analysis"}' "http://127.0.0.1:${PORT}/repository/decisions/$SMOKE_DECISION" >/dev/null
ledger="$(curl -fsS -H "$H" "http://127.0.0.1:${PORT}/audit-ledger/decisions/$SMOKE_DECISION")"; verify="$(curl -fsS -H "$H" "http://127.0.0.1:${PORT}/audit-ledger/decisions/$SMOKE_DECISION/verify")"; replay="$(curl -fsS -H "$H" "http://127.0.0.1:${PORT}/audit-ledger/decisions/$SMOKE_DECISION/replay")"
python3 - "$ledger" "$verify" "$replay" <<'PY'
import json,sys
l=json.loads(sys.argv[1]); v=json.loads(sys.argv[2]); r=json.loads(sys.argv[3])['replay']; e=l['events']
assert len(e)>=2,e
assert e[0]['previous_event_hash']=='GENESIS' and e[1]['previous_event_hash']==e[0]['event_hash'],e
assert all(len(x['payload_hash'])==64 and len(x['event_hash'])==64 for x in e),e
assert v['verification']['ok'] is True,v
assert r['mode']=='read-only-audit-replay' and r['reexecutes_domain_mutations'] is False and r['verification']['ok'] is True,r
PY
pass "decision mutations are deterministically sequenced, hash-chained, verifiable, and replayable without re-execution"

echo "=== DATABASE APPEND-ONLY TAMPER GUARD ==="
if docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "UPDATE decision_audit_events SET event_type='tampered' WHERE decision_id='${SMOKE_DECISION}';" >/dev/null 2>&1; then fail "audit ledger UPDATE unexpectedly succeeded"; fi
if docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "DELETE FROM decision_audit_events WHERE decision_id='${SMOKE_DECISION}';" >/dev/null 2>&1; then fail "audit ledger DELETE unexpectedly succeeded"; fi
pass "database rejects normal UPDATE and DELETE against decision_audit_events"

echo "=== PRESERVED LAYERS ==="; curl -fsS "http://127.0.0.1:${PORT}/auth/readiness" >/dev/null; curl -fsS "http://127.0.0.1:${PORT}/decision-rooms/contract" >/dev/null; curl -fsS "http://127.0.0.1:${PORT}/module-interoperability/contract" >/dev/null; curl -fsS "http://127.0.0.1:${PORT}/module-artifacts/contract" >/dev/null; curl -fsS "http://127.0.0.1:${PORT}/decision-composition/contract" >/dev/null; pass "v3.14 auth, v3.13 rooms, v3.12 evidence, v3.11 provenance, and v3.10 composition remain healthy"

echo "=== PUBLIC CADDY CHECK ==="; public_health="$(curl -fsS "$PUBLIC_URL/health")"; public_contract="$(curl -fsS "$PUBLIC_URL/audit-ledger/contract")"; python3 - "$public_health" "$public_contract" <<'PY'
import json,sys
h=json.loads(sys.argv[1]); c=json.loads(sys.argv[2])['audit_ledger_contract']; p=h['persistence']
assert h['version']=='3.15.0' and h['decision_event_store_schema']=='scds-decision-event-store/1.0',h
assert p['schema_revision']=='0003_v3150_event_ledger' and p['table_count']==27 and p['authority_ready'] is True,p
assert c['schema']=='scds-immutable-audit-ledger/1.0' and c['principles']['append_only'] is True,c
PY
pass "public Decision Studio API returns v3.15.0 with Decision Event Store & Immutable Audit Ledger"
echo "=== CLEAN SYNTHETIC RECORDS ==="; cleanup_smoke; SMOKE_DECISION=""; SMOKE_PROJECT=""
echo "=== FINAL CONTAINERS ==="; docker ps --filter name=sc-decision-studio --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v3.15.0 deployed with Decision Event Store & Immutable Audit Ledger"
echo "Code backup: $CODE_BACKUP"; echo "Database backup: $DB_BACKUP"; echo "Persistence credentials: $PERSIST_ENV (mode 600; do not commit)"
