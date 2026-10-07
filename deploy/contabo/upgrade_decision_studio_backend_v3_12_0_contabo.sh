#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="3.12.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v3.12.0.zip}"
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
REVISION="0001_v330_pg_foundation"
TMP="$(mktemp -d /tmp/sc-decision-studio-v3120.XXXXXX)"
SMOKE_DECISION=""; SMOKE_PROJECT=""
cleanup(){
  if [[ -n "$SMOKE_DECISION" ]] && docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
    docker exec "$DB_CONTAINER" sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -v ON_ERROR_STOP=1 -c \"DELETE FROM evidence_links WHERE decision_id='${SMOKE_DECISION}'; DELETE FROM decision_objects WHERE decision_id='${SMOKE_DECISION}'; DELETE FROM decision_events WHERE decision_id='${SMOKE_DECISION}'; DELETE FROM decisions WHERE id='${SMOKE_DECISION}'; DELETE FROM decision_projects WHERE id='${SMOKE_PROJECT}';\"" >/dev/null 2>&1 || true
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
COMPOSE_TEMPLATE="$(find "$TMP/archive" -type f -name 'compose.v3.12.0.yml' -print -quit)"
[[ -n "$SRC" && -n "$COMPOSE_TEMPLATE" ]] || fail "could not locate v3.12 backend/compose payload"
for required in app/main.py app/api/router.py app/api/routes/module_interoperability.py app/module_interoperability.py app/api/routes/module_artifacts.py app/module_artifact_provenance.py app/api/routes/composition.py app/cross_module_composition.py app/api/routes/module_registry.py app/unified_module_registry.py app/services/decision_service.py app/persistence/database.py app/persistence/models.py app/persistence/repository.py migrations/env.py migrations/versions/0001_v330_pg_foundation.py alembic.ini requirements.txt Dockerfile; do
  [[ -f "$SRC/$required" ]] || fail "v3.12 backend payload missing $required"
done
grep -q 'APP_VERSION = "3.12.0"' "$SRC/app/services/decision_service.py" || fail "payload is not v3.12.0"
grep -q 'scds-v3.12.0-module-interoperability-shared-evidence' "$SRC/app/services/decision_service.py" || fail "v3.12 fingerprint missing"
grep -q 'MODULE_INTEROPERABILITY_SCHEMA = "scds-module-interoperability/1.0"' "$SRC/app/module_interoperability.py" || fail "interoperability schema missing"
grep -q 'SHARED_EVIDENCE_SCHEMA = "scds-shared-evidence-reference/1.0"' "$SRC/app/module_interoperability.py" || fail "shared evidence schema missing"
[[ -f "$PERSIST_ENV" ]] || fail "persistence credential file missing: $PERSIST_ENV"
for key in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD SCDS_DATABASE_URL SCDS_REPOSITORY_API_KEY; do grep -q "^${key}=" "$PERSIST_ENV" || fail "$PERSIST_ENV missing $key"; done
chmod 600 "$PERSIST_ENV"
set -a; source "$PERSIST_ENV"; set +a

echo "=== PRE-FLIGHT v3.11 BASELINE ==="
preflight="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
[[ -n "$preflight" ]] || fail "current backend health unavailable"
python3 - "$preflight" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{})
assert x.get('version') in {'3.11.0','3.12.0'},x
assert p.get('authority')=='python-postgresql' and p.get('authority_ready') is True,p
assert p.get('schema_revision')=='0001_v330_pg_foundation' and p.get('table_count')==20,p
assert x.get('module_artifact_schema')=='scds-module-artifact/1.0',x
assert x.get('module_provenance_schema')=='scds-module-provenance/1.0',x
PY
pass "v3.11 artifact/provenance authority and 20-table repository baseline are current"

stamp="$(date +%Y%m%d-%H%M%S)"; backup="$BACKUP_ROOT/decision-studio-before-v3.12.0-$stamp.tgz"
echo "=== BACKUP ==="; tar -czf "$backup" -C "$ROOT" backend compose.yml .env.persistence-v330; echo "$backup"
mkdir -p "$TMP/env"
for envfile in .env .env.production; do [[ -f "$LIVE_BACKEND/$envfile" ]] && cp -a "$LIVE_BACKEND/$envfile" "$TMP/env/$envfile" || true; done
rsync -a --delete --exclude='.env' --exclude='.env.*' "$SRC/" "$LIVE_BACKEND/"
for envfile in .env .env.production; do [[ -f "$TMP/env/$envfile" ]] && cp -a "$TMP/env/$envfile" "$LIVE_BACKEND/$envfile" || true; done
cp "$COMPOSE_TEMPLATE" "$COMPOSE"
cd "$ROOT"
docker compose config --quiet

echo "=== VERIFY POSTGRESQL FOUNDATION ==="
docker compose up -d decision-studio-postgres
rev="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version LIMIT 1"')"
[[ "$rev" == "$REVISION" ]] || fail "unexpected schema revision: $rev"
tables="$(docker exec "$DB_CONTAINER" sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -Atc \"SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name <> 'alembic_version'\"")"
[[ "$tables" == "20" ]] || fail "expected 20 persistence tables, found $tables"

echo "=== BUILD v3.12.0 ==="; docker compose build "$SERVICE"
echo "=== ALEMBIC NO-OP / HEAD VERIFICATION ==="; docker compose run --rm "$SERVICE" alembic upgrade head
post_rev="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version LIMIT 1"')"; [[ "$post_rev" == "$REVISION" ]] || fail "schema revision changed unexpectedly: $post_rev"
echo "=== REFRESH MODULE REGISTRY ==="; docker compose run --rm "$SERVICE" python -m app.persistence.seed

echo "=== DEPLOY MODULE INTEROPERABILITY & SHARED EVIDENCE ==="; docker compose up -d "$SERVICE"
health=""
for _ in $(seq 1 45); do
  health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
  if [[ -n "$health" ]] && python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{}); a=x.get('release',{}).get('backend_architecture',{})
assert x.get('version')=='3.12.0'
assert x.get('build_fingerprint')=='scds-v3.12.0-module-interoperability-shared-evidence'
assert x.get('module_interoperability_schema')=='scds-module-interoperability/1.0'
assert x.get('shared_evidence_schema')=='scds-shared-evidence-reference/1.0'
assert p.get('connected') and p.get('schema_current') and p.get('authority_ready') and p.get('table_count')==20
assert a.get('route_count')==272 and a.get('router_registry_count')==22 and a.get('module_interoperability_shared_evidence') is True
PY
  then break; fi
  sleep 2
done
[[ -n "$health" ]] || { docker logs --tail=200 "$CONTAINER" >&2 || true; fail "backend did not answer /health"; }
pass "internal v3.12.0 health confirms Module Interoperability & Shared Evidence"

echo "=== INTEROPERABILITY CONTRACT SMOKE ==="
contract="$(curl -fsS "http://127.0.0.1:${PORT}/module-interoperability/contract")"
python3 - "$contract" <<'PY'
import json,sys
c=json.loads(sys.argv[1])['module_interoperability_contract']; p=c['principles']
assert c['schema']=='scds-module-interoperability/1.0' and c['shared_evidence_schema']=='scds-shared-evidence-reference/1.0',c
assert p['evidence_identity_is_shared_by_reference'] and p['evidence_payload_is_not_duplicated'] and p['owner_module_is_preserved'],p
assert p['contradictions_are_visible_not_silently_reconciled'] and p['evidence_reuse_does_not_imply_truth'] and p['evidence_reuse_does_not_imply_causality'],p
assert c['final_decision_authority']=='human-governed',c
PY
pass "interoperability contract preserves reference-only sharing, ownership, contradiction visibility, and human governance"

echo "=== AUTHORITATIVE SHARED EVIDENCE + CONTRADICTION VISIBILITY SMOKE ==="
SMOKE_PROJECT="proj-v3120-smoke-$stamp"; SMOKE_DECISION="dec-v3120-smoke-$stamp"; H="x-scds-api-key: $SCDS_REPOSITORY_API_KEY"
curl -fsS -H "$H" -H 'content-type: application/json' -d "{\"project_id\":\"$SMOKE_PROJECT\",\"title\":\"v3.12 interoperability smoke\"}" "http://127.0.0.1:${PORT}/repository/projects" >/dev/null
curl -fsS -H "$H" -H 'content-type: application/json' -d "{\"decision_id\":\"$SMOKE_DECISION\",\"project_id\":\"$SMOKE_PROJECT\",\"decision_question\":\"v3.12 shared evidence smoke\"}" "http://127.0.0.1:${PORT}/repository/decisions" >/dev/null
payload='{"shared_evidence":[{"evidence_ref":"platform-core:evidence:smoke","owner_module":"canvas","source_ref":"library:source:smoke","source_provenance_ref":"platform-core:prov:smoke","usages":[{"module_id":"canvas","relation":"supports","purpose":"Framing","claim_ref":"claim:smoke"},{"module_id":"finance","relation":"supports","purpose":"Finance context","claim_ref":"claim:smoke"},{"module_id":"narrative-risk","relation":"refutes","purpose":"Risk challenge","claim_ref":"claim:smoke"}]}],"contradiction_annotations":[{"evidence_refs":["platform-core:evidence:smoke"],"module_ids":["finance","narrative-risk"],"statement":"Explicit smoke-test disagreement."}],"artifact_links":[]}'
upserted="$(curl -fsS -X PUT -H "$H" -H 'content-type: application/json' -d "$payload" "http://127.0.0.1:${PORT}/module-interoperability/decisions/$SMOKE_DECISION")"
python3 - "$upserted" <<'PY'
import json,sys
x=json.loads(sys.argv[1])['module_interoperability']; e=x['shared_evidence'][0]
assert e['owner_module']=='canvas' and set(e['consumer_modules'])=={'canvas','finance','narrative-risk'},e
assert 'payload' not in e,e
assert x['boundaries']['ownership_transfer_on_share'] is False and x['boundaries']['truth_is_automatically_verified'] is False,x
assert len(x['integrity']['content_sha256'])==64,x
PY
eref="platform-core:evidence:smoke"
ev="$(curl -fsS -H "$H" "http://127.0.0.1:${PORT}/module-interoperability/decisions/$SMOKE_DECISION/evidence/$eref")"
python3 - "$ev" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); assert len(x['usage_edges'])==3,x
assert all(e['metadata']['ownership_transfer'] is False for e in x['usage_edges']),x
PY
diag="$(curl -fsS -H "$H" "http://127.0.0.1:${PORT}/module-interoperability/decisions/$SMOKE_DECISION/diagnostics")"
python3 - "$diag" <<'PY'
import json,sys
x=json.loads(sys.argv[1])['diagnostics']; assert x['explicit_contradiction_count']==1 and x['relation_disagreement_count']==1,x
assert x['boundaries']['relation_disagreement_is_not_truth_adjudication'] is True and x['boundaries']['contradiction_is_not_automatically_resolved'] is True,x
PY
edges="$(docker exec "$DB_CONTAINER" sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -Atc \"SELECT count(*) FROM evidence_links WHERE decision_id='${SMOKE_DECISION}' AND metadata_json->>'domain'='module-interoperability'\"")"
[[ "$edges" == "3" ]] || fail "expected 3 interoperability evidence-use edges, found $edges"
pass "shared evidence reused by stable reference with explicit module edges and contradiction visibility"

echo "=== v3.11 ARTIFACT + v3.10 COMPOSITION + v3.9 REGISTRY PRESERVATION ==="
curl -fsS "http://127.0.0.1:${PORT}/module-artifacts/contract" >/dev/null
curl -fsS "http://127.0.0.1:${PORT}/decision-composition/contract" >/dev/null
readiness="$(curl -fsS "http://127.0.0.1:${PORT}/decision-module-registry/readiness")"
python3 - "$readiness" <<'PY'
import json,sys
r=json.loads(sys.argv[1])['readiness']; assert r['ready'] and r['all_modules_authoritative'] and r['module_count']==4,r
PY
pass "v3.11 artifacts, v3.10 composition, and v3.9 Unified Decision Module Registry remain healthy"

echo "=== PUBLIC CADDY CHECK ==="
public="$(curl -fsS "$PUBLIC_URL/health")"
python3 - "$public" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x['persistence']; i=x['release']['module_interoperability']
assert x['version']=='3.12.0' and x['module_interoperability_schema']=='scds-module-interoperability/1.0' and x['shared_evidence_schema']=='scds-shared-evidence-reference/1.0',x
assert p['connected'] and p['schema_current'] and p['table_count']==20 and p['authority']=='python-postgresql',p
assert i['shared_by_reference'] and i['payload_duplicated'] is False and i['final_decision_authority']=='human-governed',i
PY
curl -fsS "$PUBLIC_URL/module-interoperability/contract" | python3 -m json.tool
pass "public Decision Studio API returns v3.12.0 with Module Interoperability & Shared Evidence"

echo "=== CLEAN SYNTHETIC RECORDS ==="; cleanup; SMOKE_DECISION=""; SMOKE_PROJECT=""
echo "=== FINAL CONTAINERS ==="; docker ps --filter "name=sc-decision-studio" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v3.12.0 deployed with Module Interoperability & Shared Evidence"
echo "Backup: $backup"
echo "Persistence credentials: $PERSIST_ENV (mode 600; do not commit)"
