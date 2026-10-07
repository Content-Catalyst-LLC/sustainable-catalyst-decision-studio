#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="3.11.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v3.11.0.zip}"
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
TMP="$(mktemp -d /tmp/sc-decision-studio-v3110.XXXXXX)"
SMOKE_DECISION=""; SMOKE_PROJECT=""
cleanup(){
  if [[ -n "$SMOKE_DECISION" ]] && docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
    docker exec "$DB_CONTAINER" sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -v ON_ERROR_STOP=1 -c \"DELETE FROM artifacts WHERE decision_id='${SMOKE_DECISION}'; DELETE FROM decisions WHERE id='${SMOKE_DECISION}'; DELETE FROM decision_projects WHERE id='${SMOKE_PROJECT}';\"" >/dev/null 2>&1 || true
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
COMPOSE_TEMPLATE="$(find "$TMP/archive" -type f -name 'compose.v3.11.0.yml' -print -quit)"
[[ -n "$SRC" && -n "$COMPOSE_TEMPLATE" ]] || fail "could not locate v3.11 backend/compose payload"
for required in app/main.py app/api/router.py app/api/routes/module_artifacts.py app/module_artifact_provenance.py app/api/routes/composition.py app/cross_module_composition.py app/api/routes/module_registry.py app/unified_module_registry.py app/services/decision_service.py app/persistence/database.py app/persistence/models.py app/persistence/repository.py migrations/env.py migrations/versions/0001_v330_pg_foundation.py alembic.ini requirements.txt Dockerfile; do
  [[ -f "$SRC/$required" ]] || fail "v3.11 backend payload missing $required"
done
grep -q 'APP_VERSION = "3.11.0"' "$SRC/app/services/decision_service.py" || fail "payload is not v3.11.0"
grep -q 'scds-v3.11.0-module-artifact-provenance-standard' "$SRC/app/services/decision_service.py" || fail "v3.11 fingerprint missing"
grep -q 'MODULE_ARTIFACT_SCHEMA = "scds-module-artifact/1.0"' "$SRC/app/module_artifact_provenance.py" || fail "artifact schema missing"
grep -q 'MODULE_PROVENANCE_SCHEMA = "scds-module-provenance/1.0"' "$SRC/app/module_artifact_provenance.py" || fail "provenance schema missing"
[[ -f "$PERSIST_ENV" ]] || fail "persistence credential file missing: $PERSIST_ENV"
for key in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD SCDS_DATABASE_URL SCDS_REPOSITORY_API_KEY; do grep -q "^${key}=" "$PERSIST_ENV" || fail "$PERSIST_ENV missing $key"; done
chmod 600 "$PERSIST_ENV"
set -a; source "$PERSIST_ENV"; set +a

echo "=== PRE-FLIGHT v3.10 BASELINE ==="
preflight="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
[[ -n "$preflight" ]] || fail "current backend health unavailable"
python3 - "$preflight" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{})
assert x.get('version') in {'3.10.0','3.11.0'},x
assert p.get('authority')=='python-postgresql' and p.get('authority_ready') is True,p
assert p.get('schema_revision')=='0001_v330_pg_foundation' and p.get('table_count')==20,p
assert x.get('cross_module_decision_composition_schema')=='scds-cross-module-decision-composition/1.0',x
PY
pass "v3.10 authoritative composition/repository baseline and 20-table schema are current"

stamp="$(date +%Y%m%d-%H%M%S)"; backup="$BACKUP_ROOT/decision-studio-before-v3.11.0-$stamp.tgz"
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
tables="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema=\047public\047 AND table_name <> \047alembic_version\047"')"
[[ "$tables" == "20" ]] || fail "expected 20 persistence tables, found $tables"

echo "=== BUILD v3.11.0 ==="; docker compose build "$SERVICE"
echo "=== ALEMBIC NO-OP / HEAD VERIFICATION ==="; docker compose run --rm "$SERVICE" alembic upgrade head
post_rev="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version LIMIT 1"')"; [[ "$post_rev" == "$REVISION" ]] || fail "schema revision changed unexpectedly: $post_rev"
echo "=== REFRESH MODULE REGISTRY ==="; docker compose run --rm "$SERVICE" python -m app.persistence.seed

echo "=== DEPLOY MODULE ARTIFACT & PROVENANCE STANDARD ==="; docker compose up -d "$SERVICE"
health=""
for _ in $(seq 1 45); do
  health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
  if [[ -n "$health" ]] && python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{}); a=x.get('release',{}).get('backend_architecture',{})
assert x.get('version')=='3.11.0'
assert x.get('build_fingerprint')=='scds-v3.11.0-module-artifact-provenance-standard'
assert x.get('module_artifact_schema')=='scds-module-artifact/1.0' and x.get('module_provenance_schema')=='scds-module-provenance/1.0'
assert p.get('connected') and p.get('schema_current') and p.get('authority_ready') and p.get('table_count')==20
assert a.get('route_count')==264 and a.get('router_registry_count')==21 and a.get('module_artifact_provenance_standard') is True
PY
  then break; fi
  sleep 2
done
[[ -n "$health" ]] || { docker logs --tail=200 "$CONTAINER" >&2 || true; fail "backend did not answer /health"; }
pass "internal v3.11.0 health confirms Module Artifact & Provenance Standard"

echo "=== ARTIFACT CONTRACT SMOKE ==="
contract="$(curl -fsS "http://127.0.0.1:${PORT}/module-artifacts/contract")"
python3 - "$contract" <<'PY'
import json,sys
c=json.loads(sys.argv[1])['module_artifact_contract']; p=c['principles']
assert c['schema']=='scds-module-artifact/1.0' and c['provenance_schema']=='scds-module-provenance/1.0',c
assert p['artifact_revisions_are_immutable'] and p['every_revision_has_sha256_integrity'] and p['parent_artifacts_are_explicit'],p
assert p['provenance_does_not_imply_truth'] and p['provenance_does_not_imply_causality'],p
assert c['compute_authorities']=={'finance':'workbench','global-impact':'workbench'},c
assert c['final_decision_authority']=='human-governed',c
PY
pass "artifact/provenance contract preserves ownership, integrity, compute, epistemic, and human-governance boundaries"

echo "=== AUTHORITATIVE ARTIFACT REVISION + LINEAGE SMOKE ==="
SMOKE_PROJECT="proj-v3110-smoke-$stamp"; SMOKE_DECISION="dec-v3110-smoke-$stamp"; H="x-scds-api-key: $SCDS_REPOSITORY_API_KEY"
curl -fsS -H "$H" -H 'content-type: application/json' -d "{\"project_id\":\"$SMOKE_PROJECT\",\"title\":\"v3.11 artifact smoke\"}" "http://127.0.0.1:${PORT}/repository/projects" >/dev/null
curl -fsS -H "$H" -H 'content-type: application/json' -d "{\"decision_id\":\"$SMOKE_DECISION\",\"project_id\":\"$SMOKE_PROJECT\",\"decision_question\":\"v3.11 provenance smoke\"}" "http://127.0.0.1:${PORT}/repository/decisions" >/dev/null
created="$(curl -fsS -H "$H" -H 'content-type: application/json' -d '{"module_id":"finance","artifact_type":"valuation-context","title":"Smoke artifact","payload":{"discount_rate":0.08},"evidence_refs":["evidence:smoke"],"computation_refs":["workbench:smoke-1"],"provenance":{"methodology":"smoke"}}' "http://127.0.0.1:${PORT}/module-artifacts/decisions/$SMOKE_DECISION")"
logical="$(python3 - "$created" <<'PY'
import json,sys
x=json.loads(sys.argv[1])['module_artifact']; assert x['revision_no']==1 and len(x['integrity']['content_sha256'])==64,x; print(x['artifact_id'])
PY
)"
rev1="$(python3 - "$created" <<'PY'
import json,sys; print(json.loads(sys.argv[1])['module_artifact']['revision_id'])
PY
)"
revised="$(curl -fsS -X POST -H "$H" -H 'content-type: application/json' -d '{"module_id":"finance","payload":{"discount_rate":0.09},"computation_refs":["workbench:smoke-2"]}' "http://127.0.0.1:${PORT}/module-artifacts/decisions/$SMOKE_DECISION/$logical/revisions")"
python3 - "$revised" "$rev1" <<'PY'
import json,sys
x=json.loads(sys.argv[1])['module_artifact']; rev1=sys.argv[2]
assert x['revision_no']==2 and rev1 in x['parent_artifact_ids'] and len(x['integrity']['content_sha256'])==64,x
assert x['ownership']['module_id']=='finance' and x['ownership']['compute_authority']=='workbench',x
PY
historical="$(curl -fsS -H "$H" "http://127.0.0.1:${PORT}/module-artifacts/decisions/$SMOKE_DECISION/$rev1")"
python3 - "$historical" <<'PY'
import json,sys
x=json.loads(sys.argv[1])['module_artifact']; assert x['revision_no']==1 and x['payload']['discount_rate']==0.08,x
PY
lineage="$(curl -fsS -H "$H" "http://127.0.0.1:${PORT}/module-artifacts/decisions/$SMOKE_DECISION/$logical/lineage")"
python3 - "$lineage" <<'PY'
import json,sys
x=json.loads(sys.argv[1])['lineage']; b=x['boundaries']
assert x['revision_count']==2 and x['current_revision_no']==2 and len(x['edges'])>=1,x
assert b['lineage_implies_truth'] is False and b['lineage_implies_causality'] is False and b['final_decision_authority']=='human-governed',b
PY
pass "immutable revision history, historical read, SHA-256 integrity, and lineage reconstruction succeeded"

echo "=== v3.10 COMPOSITION + v3.9 REGISTRY PRESERVATION ==="
curl -fsS "http://127.0.0.1:${PORT}/decision-composition/contract" >/dev/null
readiness="$(curl -fsS "http://127.0.0.1:${PORT}/decision-module-registry/readiness")"
python3 - "$readiness" <<'PY'
import json,sys
r=json.loads(sys.argv[1])['readiness']; assert r['ready'] and r['all_modules_authoritative'] and r['module_count']==4,r
PY
pass "cross-module composition and Unified Decision Module Registry remain healthy"

echo "=== PUBLIC CADDY CHECK ==="
public="$(curl -fsS "$PUBLIC_URL/health")"
python3 - "$public" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x['persistence']; a=x['release']['module_artifact_provenance']
assert x['version']=='3.11.0' and x['module_artifact_schema']=='scds-module-artifact/1.0' and x['module_provenance_schema']=='scds-module-provenance/1.0',x
assert p['connected'] and p['schema_current'] and p['table_count']==20 and p['authority']=='python-postgresql',p
assert a['immutable_revisions'] and a['sha256_integrity'] and a['final_decision_authority']=='human-governed',a
PY
curl -fsS "$PUBLIC_URL/module-artifacts/contract" | python3 -m json.tool
pass "public Decision Studio API returns v3.11.0 with canonical Module Artifact & Provenance Standard"

echo "=== CLEAN SYNTHETIC RECORDS ==="; cleanup; SMOKE_DECISION=""; SMOKE_PROJECT=""
echo "=== FINAL CONTAINERS ==="; docker ps --filter "name=sc-decision-studio" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v3.11.0 deployed with canonical Module Artifact & Provenance Standard"
echo "Backup: $backup"
echo "Persistence credentials: $PERSIST_ENV (mode 600; do not commit)"
