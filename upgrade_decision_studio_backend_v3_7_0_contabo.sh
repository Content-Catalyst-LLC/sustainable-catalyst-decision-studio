#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="3.7.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v3.7.0.zip}"
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
TMP="$(mktemp -d /tmp/sc-decision-studio-v370.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }
pass(){ echo "PASS: $*"; }

[[ -f "$ARCHIVE" ]] || fail "backend archive not found: $ARCHIVE"
[[ -d "$ROOT" && -f "$COMPOSE" ]] || fail "Decision Studio runtime root/compose missing: $ROOT"
for c in docker python3 unzip rsync curl tar; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
mkdir -p "$BACKUP_ROOT"
unzip -q "$ARCHIVE" -d "$TMP/archive"
SRC="$(find "$TMP/archive" -type f -path '*/backend/app/main.py' -print -quit | sed 's#/app/main.py$##')"
COMPOSE_TEMPLATE="$(find "$TMP/archive" -type f -name 'compose.v3.7.0.yml' -print -quit)"
[[ -n "$SRC" && -n "$COMPOSE_TEMPLATE" ]] || fail "could not locate v3.7 backend/compose payload"
for required in app/main.py app/api/router.py app/api/routes/repository.py app/api/routes/canvas.py app/api/routes/finance.py app/api/routes/narrative_risk.py app/services/decision_service.py app/domains/canvas.py app/domains/finance.py app/domains/narrative_risk.py app/persistence/database.py app/persistence/models.py app/persistence/contracts.py app/persistence/repository.py app/persistence/seed.py migrations/env.py migrations/versions/0001_v330_pg_foundation.py alembic.ini requirements.txt Dockerfile; do
  [[ -f "$SRC/$required" ]] || fail "v3.7 backend payload missing $required"
done
grep -q 'APP_VERSION = "3.7.0"' "$SRC/app/services/decision_service.py" || fail "payload is not Decision Studio v3.7.0"
grep -q 'scds-v3.7.0-narrative-risk-python-domain-migration' "$SRC/app/services/decision_service.py" || fail "v3.7 fingerprint missing"
grep -q 'NARRATIVE_RISK_DOMAIN_SCHEMA = "scds-narrative-risk-domain/1.0"' "$SRC/app/domains/narrative_risk.py" || fail "Narrative Risk domain schema missing"
grep -q 'FINANCE_DOMAIN_SCHEMA = "scds-finance-domain/1.0"' "$SRC/app/domains/finance.py" || fail "Finance preservation missing"
grep -q 'CANVAS_DOMAIN_SCHEMA = "scds-canvas-domain/1.0"' "$SRC/app/domains/canvas.py" || fail "Canvas preservation missing"
grep -q 'PERSISTENCE_AUTHORITY = "python-postgresql"' "$SRC/app/persistence/database.py" || fail "authoritative persistence boundary missing"
grep -q 'SCDS_PERSISTENCE_WRITE_ENABLED: "true"' "$COMPOSE_TEMPLATE" || fail "v3.7 compose does not preserve repository writes"

echo "=== PRE-FLIGHT ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' || true
preflight="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
if [[ -n "$preflight" ]]; then
  python3 - "$preflight" <<'PY'
import json,sys
x=json.loads(sys.argv[1])
assert x.get('version') in {'3.6.0','3.7.0'}, x
p=x.get('persistence',{})
assert p.get('authority')=='python-postgresql' and p.get('authority_ready') is True, p
if x.get('version')=='3.6.0':
    assert x.get('canvas_domain_schema')=='scds-canvas-domain/1.0', x
    assert x.get('finance_domain_schema')=='scds-finance-domain/1.0', x
PY
fi
[[ -f "$PERSIST_ENV" ]] || fail "persistence credential file missing: $PERSIST_ENV"
for key in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD SCDS_DATABASE_URL SCDS_REPOSITORY_API_KEY; do grep -q "^${key}=" "$PERSIST_ENV" || fail "$PERSIST_ENV missing $key"; done
chmod 600 "$PERSIST_ENV"
REPO_API_KEY="$(grep '^SCDS_REPOSITORY_API_KEY=' "$PERSIST_ENV" | tail -1 | cut -d= -f2-)"
[[ -n "$REPO_API_KEY" ]] || fail "repository API key is empty"

stamp="$(date +%Y%m%d-%H%M%S)"
backup="$BACKUP_ROOT/decision-studio-before-v3.7.0-$stamp.tgz"
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

echo "=== VERIFY v3.6 CANVAS + FINANCE + REPOSITORY BASELINE ==="
docker compose up -d "$DB_SERVICE"
for _ in $(seq 1 60); do
  if docker exec "$DB_CONTAINER" sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then break; fi
  sleep 2
done
docker exec "$DB_CONTAINER" sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1 || fail "PostgreSQL did not become ready"
current_revision="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version LIMIT 1"' || true)"
[[ "$current_revision" == "$REVISION" ]] || fail "v3.7 requires revision $REVISION; found ${current_revision:-<none>}"
table_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema='"'"'public'"'"' AND table_type='"'"'BASE TABLE'"'"' AND table_name <> '"'"'alembic_version'"'"'"')"
[[ "$table_count" == "20" ]] || fail "expected 20 persistence tables, got $table_count"
canvas_status="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT status FROM decision_modules WHERE module_id='"'"'canvas'"'"'"' || true)"
finance_status="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT status FROM decision_modules WHERE module_id='"'"'finance'"'"'"' || true)"
[[ "$canvas_status" == "python-domain-authoritative" ]] || fail "v3.7 requires Canvas authority; found $canvas_status"
[[ "$finance_status" == "python-domain-authoritative" ]] || fail "v3.7 requires Finance authority; found $finance_status"
pass "v3.6 Canvas + Finance + authoritative repository baseline is current"

echo "=== BUILD v3.7.0 BACKEND ==="
docker compose build "$SERVICE"

echo "=== ALEMBIC NO-OP / HEAD VERIFICATION ==="
docker compose run --rm "$SERVICE" alembic upgrade head
revision="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version LIMIT 1"')"
[[ "$revision" == "$REVISION" ]] || fail "schema revision changed unexpectedly: $revision"

echo "=== REFRESH MODULE REGISTRY ==="
docker compose run --rm "$SERVICE" python -m app.persistence.seed
canvas_status="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT status FROM decision_modules WHERE module_id='"'"'canvas'"'"'"')"
finance_status="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT status FROM decision_modules WHERE module_id='"'"'finance'"'"'"')"
risk_status="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT status FROM decision_modules WHERE module_id='"'"'narrative-risk'"'"'"')"
global_status="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT status FROM decision_modules WHERE module_id='"'"'global-impact'"'"'"')"
[[ "$canvas_status" == "python-domain-authoritative" ]] || fail "Canvas authority regressed: $canvas_status"
[[ "$finance_status" == "python-domain-authoritative" ]] || fail "Finance authority regressed: $finance_status"
[[ "$risk_status" == "python-domain-authoritative" ]] || fail "Narrative Risk module registry status not migrated: $risk_status"
[[ "$global_status" == "foundation" ]] || fail "Global Impact should remain foundation in v3.7; found $global_status"
pass "Canvas, Finance, and Narrative Risk are python-domain-authoritative; Global Impact remains foundation"

echo "=== DEPLOY NARRATIVE RISK PYTHON DOMAIN ==="
docker compose up -d --force-recreate "$SERVICE"
health=""
for _ in $(seq 1 60); do
  if health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null)"; then
    if python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{}); a=x.get('release',{}).get('backend_architecture',{})
assert x.get('ok') is True and x.get('ready') is True
assert x.get('version')=='3.7.0'
assert x.get('build_fingerprint')=='scds-v3.7.0-narrative-risk-python-domain-migration'
assert x.get('source_commit')=='release-v3.7.0'
assert x.get('canvas_domain_schema')=='scds-canvas-domain/1.0'
assert x.get('finance_domain_schema')=='scds-finance-domain/1.0'
assert x.get('narrative_risk_domain_schema')=='scds-narrative-risk-domain/1.0'
assert p.get('connected') is True and p.get('schema_current') is True and p.get('authority_ready') is True
assert p.get('schema_revision')=='0001_v330_pg_foundation' and p.get('table_count')==20
assert a.get('database_migration') is False and a.get('narrative_risk_python_domain_migration') is True
PY
    then break; fi
  fi
  sleep 2
done
[[ -n "$health" ]] || { docker logs --tail=200 "$CONTAINER" >&2 || true; fail "backend did not answer /health"; }
python3 - "$health" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x['persistence']; a=x['release']['backend_architecture']; n=x['release']['narrative_risk']; f=x['release']['finance']; c=x['release']['canvas']
assert x['version']=='3.7.0',x
assert p['connected'] and p['schema_current'] and p['authority_ready'],p
assert p['table_count']==20 and p['authority']=='python-postgresql',p
assert a['route_count']==231 and a['router_registry_count']==17,a
assert a['database_migration'] is False and a['narrative_risk_python_domain_migration'] is True,a
assert a['finance_python_domain_migration'] is False,a
assert n['schema']=='scds-narrative-risk-domain/1.0' and n['status']=='python-domain-authoritative',n
assert n['automatic_truth_verification'] is False and n['automatic_causality_inference'] is False,n
assert f['status']=='python-domain-authoritative' and f['compute_authority']=='workbench',f
assert c['status']=='python-domain-authoritative',c
print('PASS: internal v3.7.0 health confirms Narrative Risk Python domain migration')
PY

echo "=== NARRATIVE RISK CONTRACT SMOKE ==="
risk_contract="$(curl -fsS "http://127.0.0.1:${PORT}/narrative-risk/contract")"
python3 - "$risk_contract" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); n=x['narrative_risk_contract']; b=n['boundaries']
assert x['version']=='3.7.0' and n['schema']=='scds-narrative-risk-domain/1.0',x
assert n['status']=='python-domain-authoritative' and n['storage_authority']=='python-postgresql',n
assert b['claim_is_not_fact_without_evidence'] is True and b['signal_is_not_causality'] is True,b
assert b['automatic_truth_verification'] is False and b['automatic_causality_inference'] is False,b
assert b['automatic_recommendation'] is False and b['automatic_escalation_or_action'] is False,b
assert b['final_decision_authority']=='human-governed'
print('PASS: Narrative Risk domain contract is live with explicit epistemic boundaries')
PY

echo "=== AUTHORITATIVE NARRATIVE RISK WRITE/READ + DOMAIN ISOLATION SMOKE ==="
docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "DELETE FROM decisions WHERE id='"'"'v370-deploy-smoke-decision'"'"'; DELETE FROM decision_projects WHERE id='"'"'v370-deploy-smoke-project'"'"';"' >/dev/null
curl -fsS -X POST "http://127.0.0.1:${PORT}/repository/projects" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"project_id":"v370-deploy-smoke-project","title":"v3.7 Narrative Risk deployment smoke"}' >/dev/null
curl -fsS -X POST "http://127.0.0.1:${PORT}/repository/decisions" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"decision_id":"v370-deploy-smoke-decision","project_id":"v370-deploy-smoke-project","decision_question":"Which emerging narrative risks require governed review?"}' >/dev/null
# Establish a Finance-owned artifact to prove Narrative Risk signal replacement cannot delete it.
curl -fsS -X PUT "http://127.0.0.1:${PORT}/finance/decisions/v370-deploy-smoke-decision" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"workbench_receipts":[{"id":"finance-r","uri":"workbench://jobs/v370-finance-smoke"}]}' >/dev/null
risk_write="$(curl -fsS -X PUT "http://127.0.0.1:${PORT}/narrative-risk/decisions/v370-deploy-smoke-decision" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"risk_context":{"scope":"emerging-risk"},"actors":[{"id":"actor-1","name":"Supplier network"}],"exposures":[{"id":"exp-1","type":"operational"}],"narratives":[{"id":"n1","label":"Supply disruption may persist"}],"claims":[{"id":"claim-1","text":"Supplier concentration may increase disruption exposure.","kind":"risk-hypothesis","epistemic_status":"unresolved"}],"signals":[{"id":"signal-1","label":"Extended outage report","signal_type":"operational","source_ref":"site-intelligence:signal:v370"}],"evidence_links":[{"id":"link-1","claim_id":"claim-1","evidence_ref":"library:evidence:v370","relation":"supports"}],"watch_conditions":[{"id":"watch-1","condition":"Outage exceeds 48 hours"}],"provenance":{"source":"deploy-v3.7.0"}}')"
risk_read="$(curl -fsS "http://127.0.0.1:${PORT}/narrative-risk/decisions/v370-deploy-smoke-decision" -H "X-SCDS-API-Key: $REPO_API_KEY")"
python3 - "$risk_write" "$risk_read" <<'PY'
import json,sys
w,r=map(json.loads,sys.argv[1:])
for x in (w,r):
    n=x['narrative_risk']
    assert n['schema']=='scds-narrative-risk-domain/1.0'
    assert len(n['claims'])==1 and len(n['signals'])==1 and len(n['evidence_links'])==1
    assert n['boundaries']['automatic_truth_verification'] is False
    assert n['boundaries']['automatic_causality_inference'] is False
print('PASS: authoritative Narrative Risk write/read round trip succeeded')
PY
# Replace Narrative Risk signals; Finance artifact must survive.
curl -fsS -X PUT "http://127.0.0.1:${PORT}/narrative-risk/decisions/v370-deploy-smoke-decision/signals" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"signals":[{"id":"signal-2","label":"Updated outage signal"}]}' >/dev/null
claim_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM claims WHERE decision_id='"'"'v370-deploy-smoke-decision'"'"' AND metadata_json->>'"'"'domain'"'"'='"'"'narrative-risk'"'"'"')"
link_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM evidence_links WHERE decision_id='"'"'v370-deploy-smoke-decision'"'"' AND metadata_json->>'"'"'domain'"'"'='"'"'narrative-risk'"'"'"')"
signal_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM artifacts WHERE decision_id='"'"'v370-deploy-smoke-decision'"'"' AND artifact_type='"'"'narrative-risk-signal'"'"'"')"
finance_receipt_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM artifacts WHERE decision_id='"'"'v370-deploy-smoke-decision'"'"' AND artifact_type='"'"'finance-workbench-receipt'"'"'"')"
[[ "$claim_count" == "1" && "$link_count" == "1" && "$signal_count" == "1" && "$finance_receipt_count" == "1" ]] || fail "Narrative Risk normalization/isolation invalid: claims=$claim_count links=$link_count signals=$signal_count finance_receipts=$finance_receipt_count"
pass "Narrative Risk claim/evidence/signal normalization and Finance artifact isolation verified"
docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "DELETE FROM decisions WHERE id='"'"'v370-deploy-smoke-decision'"'"'; DELETE FROM decision_projects WHERE id='"'"'v370-deploy-smoke-project'"'"';"' >/dev/null

echo "=== MODULE AUTHORITY BOUNDARIES ==="
mods="$(curl -fsS "http://127.0.0.1:${PORT}/decision-modules")"
python3 - "$mods" <<'PY'
import json,sys
r=json.loads(sys.argv[1])['registry']; mods={m['module_id']:m for m in r['modules']}
assert r['module_count']==4 and set(mods)=={'canvas','finance','narrative-risk','global-impact'},r
for mid in ('canvas','finance','narrative-risk'):
    assert mods[mid]['status']=='python-domain-authoritative' and mods[mid]['storage_authority']=='python-postgresql',mods[mid]
assert mods['finance']['providers']['compute_authority']=='workbench',mods['finance']
assert mods['narrative-risk']['providers']['persistence_authority']=='python-postgresql',mods['narrative-risk']
assert mods['global-impact']['status']=='foundation',mods['global-impact']
print('PASS: Canvas + Finance + Narrative Risk authoritative; Global Impact remains staged; Workbench retains Finance compute authority')
PY

echo "=== PUBLIC CADDY CHECK ==="
public="$(curl -fsS "$PUBLIC_URL/health")"
python3 - "$public" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x['persistence']; n=x['release']['narrative_risk']; f=x['release']['finance']
assert x['version']=='3.7.0' and x['build_fingerprint']=='scds-v3.7.0-narrative-risk-python-domain-migration',x
assert x['narrative_risk_domain_schema']=='scds-narrative-risk-domain/1.0',x
assert p['connected'] and p['schema_current'] and p['authority']=='python-postgresql',p
assert p['write_enabled'] is True and p['authority_ready'] is True,p
assert n['status']=='python-domain-authoritative' and n['automatic_truth_verification'] is False,n
assert f['compute_authority']=='workbench' and f['decision_studio_executes_financial_models'] is False,f
print('PASS: public Decision Studio API returns v3.7.0 with authoritative Narrative Risk domain')
PY
curl -fsS "$PUBLIC_URL/narrative-risk/contract" | python3 -m json.tool

echo "=== FINAL CONTAINERS ==="
docker ps --filter "name=sc-decision-studio" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v3.7.0 deployed with Narrative Risk Python domain authority and explicit epistemic boundaries"
echo "Backup: $backup"
echo "Persistence credentials: $PERSIST_ENV (mode 600; do not commit)"
