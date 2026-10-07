#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="3.8.0"
ARCHIVE="${1:-/tmp/sustainable-catalyst-decision-studio-backend-v3.8.0.zip}"
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
TMP="$(mktemp -d /tmp/sc-decision-studio-v380.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }
pass(){ echo "PASS: $*"; }

[[ -f "$ARCHIVE" ]] || fail "backend archive not found: $ARCHIVE"
[[ -d "$ROOT" && -f "$COMPOSE" ]] || fail "Decision Studio runtime root/compose missing: $ROOT"
for c in docker python3 unzip rsync curl tar; do command -v "$c" >/dev/null 2>&1 || fail "$c is required"; done
mkdir -p "$BACKUP_ROOT"
unzip -q "$ARCHIVE" -d "$TMP/archive"
SRC="$(find "$TMP/archive" -type f -path '*/backend/app/main.py' -print -quit | sed 's#/app/main.py$##')"
COMPOSE_TEMPLATE="$(find "$TMP/archive" -type f -name 'compose.v3.8.0.yml' -print -quit)"
[[ -n "$SRC" && -n "$COMPOSE_TEMPLATE" ]] || fail "could not locate v3.8 backend/compose payload"
for required in app/main.py app/api/router.py app/api/routes/repository.py app/api/routes/canvas.py app/api/routes/finance.py app/api/routes/narrative_risk.py app/api/routes/global_impact.py app/services/decision_service.py app/domains/canvas.py app/domains/finance.py app/domains/narrative_risk.py app/domains/global_impact.py app/persistence/database.py app/persistence/models.py app/persistence/contracts.py app/persistence/repository.py app/persistence/seed.py migrations/env.py migrations/versions/0001_v330_pg_foundation.py alembic.ini requirements.txt Dockerfile; do
  [[ -f "$SRC/$required" ]] || fail "v3.8 backend payload missing $required"
done
grep -q 'APP_VERSION = "3.8.0"' "$SRC/app/services/decision_service.py" || fail "payload is not Decision Studio v3.8.0"
grep -q 'scds-v3.8.0-global-impact-catalyst-python-domain-migration' "$SRC/app/services/decision_service.py" || fail "v3.8 fingerprint missing"
grep -q 'GLOBAL_IMPACT_DOMAIN_SCHEMA = "scds-global-impact-domain/1.0"' "$SRC/app/domains/global_impact.py" || fail "Global Impact domain schema missing"
grep -q 'NARRATIVE_RISK_DOMAIN_SCHEMA = "scds-narrative-risk-domain/1.0"' "$SRC/app/domains/narrative_risk.py" || fail "Narrative Risk preservation missing"
grep -q 'FINANCE_DOMAIN_SCHEMA = "scds-finance-domain/1.0"' "$SRC/app/domains/finance.py" || fail "Finance preservation missing"
grep -q 'CANVAS_DOMAIN_SCHEMA = "scds-canvas-domain/1.0"' "$SRC/app/domains/canvas.py" || fail "Canvas preservation missing"
grep -q 'PERSISTENCE_AUTHORITY = "python-postgresql"' "$SRC/app/persistence/database.py" || fail "authoritative persistence boundary missing"
grep -q 'SCDS_PERSISTENCE_WRITE_ENABLED: "true"' "$COMPOSE_TEMPLATE" || fail "v3.8 compose does not preserve repository writes"

[[ -f "$PERSIST_ENV" ]] || fail "persistence credential file missing: $PERSIST_ENV"
for key in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD SCDS_DATABASE_URL SCDS_REPOSITORY_API_KEY; do grep -q "^${key}=" "$PERSIST_ENV" || fail "$PERSIST_ENV missing $key"; done
chmod 600 "$PERSIST_ENV"
REPO_API_KEY="$(grep '^SCDS_REPOSITORY_API_KEY=' "$PERSIST_ENV" | tail -1 | cut -d= -f2-)"
[[ -n "$REPO_API_KEY" ]] || fail "repository API key is empty"

echo "=== PRE-FLIGHT ==="
docker ps --filter "name=$CONTAINER" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' || true
preflight="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
if [[ -n "$preflight" ]]; then
  python3 - "$preflight" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{})
assert x.get('version') in {'3.7.0','3.8.0'}, x
assert p.get('authority')=='python-postgresql' and p.get('authority_ready') is True, p
if x.get('version')=='3.7.0':
    assert x.get('canvas_domain_schema')=='scds-canvas-domain/1.0', x
    assert x.get('finance_domain_schema')=='scds-finance-domain/1.0', x
    assert x.get('narrative_risk_domain_schema')=='scds-narrative-risk-domain/1.0', x
PY
fi

stamp="$(date +%Y%m%d-%H%M%S)"
backup="$BACKUP_ROOT/decision-studio-before-v3.8.0-$stamp.tgz"
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

echo "=== VERIFY v3.7 CANVAS + FINANCE + NARRATIVE RISK + REPOSITORY BASELINE ==="
docker compose up -d "$DB_SERVICE"
for _ in $(seq 1 40); do
  if docker inspect -f '{{.State.Health.Status}}' "$DB_CONTAINER" 2>/dev/null | grep -q healthy; then break; fi
  sleep 2
done
[[ "$(docker inspect -f '{{.State.Health.Status}}' "$DB_CONTAINER" 2>/dev/null || true)" == "healthy" ]] || fail "PostgreSQL is not healthy"
current_rev="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version LIMIT 1"')"
[[ "$current_rev" == "$REVISION" ]] || fail "expected Alembic revision $REVISION, got $current_rev"
table_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema='"'"'public'"'"' AND table_name NOT IN ('"'"'alembic_version'"'"')"')"
[[ "$table_count" == "20" ]] || fail "expected 20 Decision Studio persistence tables, got $table_count"
pass "v3.7 authoritative repository and 20-table schema are current"

echo "=== BUILD v3.8.0 ==="
docker compose build "$SERVICE"

echo "=== ALEMBIC NO-OP / HEAD VERIFICATION ==="
docker compose run --rm "$SERVICE" alembic upgrade head
post_rev="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version LIMIT 1"')"
[[ "$post_rev" == "$REVISION" ]] || fail "schema revision changed unexpectedly: $post_rev"

echo "=== REFRESH MODULE REGISTRY ==="
docker compose run --rm "$SERVICE" python -m app.persistence.seed
module_state="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT module_id||'"'"':'"'"'||status FROM decision_modules ORDER BY module_id"')"
python3 - "$module_state" <<'PY'
import sys
rows=dict(line.split(':',1) for line in sys.argv[1].splitlines() if ':' in line)
assert set(rows)=={'canvas','finance','global-impact','narrative-risk'},rows
for mid in rows:
    assert rows[mid]=='python-domain-authoritative',(mid,rows[mid])
print('PASS: all four Decision Studio modules are python-domain-authoritative')
PY

echo "=== DEPLOY GLOBAL IMPACT CATALYST PYTHON DOMAIN ==="
docker compose up -d "$SERVICE"
health=""
for _ in $(seq 1 45); do
  health="$(curl -fsS "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
  if [[ -n "$health" ]] && python3 - "$health" <<'PY' >/dev/null 2>&1
import json,sys
x=json.loads(sys.argv[1]); p=x.get('persistence',{}); a=x.get('release',{}).get('backend_architecture',{})
assert x.get('ok') is True and x.get('ready') is True
assert x.get('version')=='3.8.0'
assert x.get('build_fingerprint')=='scds-v3.8.0-global-impact-catalyst-python-domain-migration'
assert x.get('source_commit')=='release-v3.8.0'
assert x.get('canvas_domain_schema')=='scds-canvas-domain/1.0'
assert x.get('finance_domain_schema')=='scds-finance-domain/1.0'
assert x.get('narrative_risk_domain_schema')=='scds-narrative-risk-domain/1.0'
assert x.get('global_impact_domain_schema')=='scds-global-impact-domain/1.0'
assert p.get('connected') is True and p.get('schema_current') is True and p.get('authority_ready') is True
assert p.get('schema_revision')=='0001_v330_pg_foundation' and p.get('table_count')==20
assert a.get('database_migration') is False and a.get('global_impact_python_domain_migration') is True
PY
  then break; fi
  sleep 2
done
[[ -n "$health" ]] || { docker logs --tail=200 "$CONTAINER" >&2 || true; fail "backend did not answer /health"; }
python3 - "$health" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x['persistence']; a=x['release']['backend_architecture']; g=x['release']['global_impact']; n=x['release']['narrative_risk']; f=x['release']['finance']; c=x['release']['canvas']
assert x['version']=='3.8.0',x
assert p['connected'] and p['schema_current'] and p['authority_ready'],p
assert p['table_count']==20 and p['authority']=='python-postgresql',p
assert a['route_count']==242 and a['router_registry_count']==18,a
assert a['database_migration'] is False and a['global_impact_python_domain_migration'] is True,a
assert g['schema']=='scds-global-impact-domain/1.0' and g['status']=='python-domain-authoritative',g
assert g['compute_authority']=='workbench' and g['decision_studio_executes_impact_models'] is False,g
assert g['automatic_impact_verification'] is False and g['automatic_sustainability_rating'] is False,g
assert n['status']=='python-domain-authoritative',n
assert f['status']=='python-domain-authoritative' and f['compute_authority']=='workbench',f
assert c['status']=='python-domain-authoritative',c
print('PASS: internal v3.8.0 health confirms Global Impact Catalyst Python domain migration')
PY

echo "=== GLOBAL IMPACT CONTRACT SMOKE ==="
impact_contract="$(curl -fsS "http://127.0.0.1:${PORT}/global-impact/contract")"
python3 - "$impact_contract" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); g=x['global_impact_contract']; b=g['boundaries']
assert x['version']=='3.8.0' and g['schema']=='scds-global-impact-domain/1.0',x
assert g['status']=='python-domain-authoritative' and g['storage_authority']=='python-postgresql',g
assert g['compute_authority']=='workbench',g
assert b['sdg_alignment_is_not_proof_of_impact'] is True and b['modeled_impact_is_not_observed_outcome'] is True,b
assert b['indicator_change_is_not_causal_attribution'] is True,b
assert b['decision_studio_executes_impact_models'] is False,b
assert b['automatic_impact_verification'] is False and b['automatic_sustainability_rating'] is False,b
assert b['automatic_recommendation'] is False and b['automatic_approval'] is False,b
assert b['final_decision_authority']=='human-governed'
print('PASS: Global Impact domain contract is live with explicit impact and compute boundaries')
PY

echo "=== AUTHORITATIVE GLOBAL IMPACT WRITE/READ + DOMAIN ISOLATION SMOKE ==="
docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "DELETE FROM decisions WHERE id='"'"'v380-deploy-smoke-decision'"'"'; DELETE FROM decision_projects WHERE id='"'"'v380-deploy-smoke-project'"'"';"' >/dev/null
curl -fsS -X POST "http://127.0.0.1:${PORT}/repository/projects" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"project_id":"v380-deploy-smoke-project","title":"v3.8 Global Impact deployment smoke"}' >/dev/null
curl -fsS -X POST "http://127.0.0.1:${PORT}/repository/decisions" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"decision_id":"v380-deploy-smoke-decision","project_id":"v380-deploy-smoke-project","decision_question":"Which option has the most accountable impact profile?"}' >/dev/null
# Establish prior-domain artifacts to prove Global Impact indicator replacement cannot delete them.
curl -fsS -X PUT "http://127.0.0.1:${PORT}/finance/decisions/v380-deploy-smoke-decision" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"workbench_receipts":[{"id":"finance-r","uri":"workbench://finance/v380"}]}' >/dev/null
curl -fsS -X PUT "http://127.0.0.1:${PORT}/narrative-risk/decisions/v380-deploy-smoke-decision" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"signals":[{"id":"risk-s","label":"Policy uncertainty signal"}]}' >/dev/null
impact_write="$(curl -fsS -X PUT "http://127.0.0.1:${PORT}/global-impact/decisions/v380-deploy-smoke-decision" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"impact_context":{"scope":"regional-transition"},"sdg_alignments":[{"sdg":"SDG 7","alignment":"contextual"}],"impact_claims":[{"id":"claim-1","text":"Lifecycle emissions may decline.","impact_dimension":"environmental"}],"indicators":[{"id":"ind-1","label":"Lifecycle GHG intensity","unit":"kgCO2e/unit","observed":false}],"evidence_links":[{"id":"link-1","claim_id":"claim-1","evidence_ref":"library:evidence:v380","relation":"supports"}],"provenance":{"source":"deploy-v3.8.0"}}')"
impact_read="$(curl -fsS "http://127.0.0.1:${PORT}/global-impact/decisions/v380-deploy-smoke-decision" -H "X-SCDS-API-Key: $REPO_API_KEY")"
python3 - "$impact_write" "$impact_read" <<'PY'
import json,sys
w,r=map(json.loads,sys.argv[1:])
for x in (w,r):
    g=x['global_impact']
    assert g['schema']=='scds-global-impact-domain/1.0'
    assert len(g['impact_claims'])==1 and len(g['indicators'])==1 and len(g['evidence_links'])==1
    assert g['boundaries']['automatic_impact_verification'] is False
    assert g['boundaries']['automatic_sustainability_rating'] is False
print('PASS: authoritative Global Impact write/read round trip succeeded')
PY
curl -fsS -X PUT "http://127.0.0.1:${PORT}/global-impact/decisions/v380-deploy-smoke-decision/indicators" -H 'Content-Type: application/json' -H "X-SCDS-API-Key: $REPO_API_KEY" -d '{"indicators":[{"id":"ind-2","label":"Water intensity"}]}' >/dev/null
impact_claim_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM claims WHERE decision_id='"'"'v380-deploy-smoke-decision'"'"' AND metadata_json->>'"'"'domain'"'"'='"'"'global-impact'"'"'"')"
impact_link_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM evidence_links WHERE decision_id='"'"'v380-deploy-smoke-decision'"'"' AND metadata_json->>'"'"'domain'"'"'='"'"'global-impact'"'"'"')"
impact_indicator_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM artifacts WHERE decision_id='"'"'v380-deploy-smoke-decision'"'"' AND artifact_type='"'"'global-impact-indicator'"'"'"')"
finance_receipt_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM artifacts WHERE decision_id='"'"'v380-deploy-smoke-decision'"'"' AND artifact_type='"'"'finance-workbench-receipt'"'"'"')"
risk_signal_count="$(docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM artifacts WHERE decision_id='"'"'v380-deploy-smoke-decision'"'"' AND artifact_type='"'"'narrative-risk-signal'"'"'"')"
[[ "$impact_claim_count" == "1" && "$impact_link_count" == "1" && "$impact_indicator_count" == "1" && "$finance_receipt_count" == "1" && "$risk_signal_count" == "1" ]] || fail "Global Impact normalization/isolation invalid: claims=$impact_claim_count links=$impact_link_count indicators=$impact_indicator_count finance=$finance_receipt_count risk=$risk_signal_count"
pass "Global Impact claim/evidence/indicator normalization and cross-domain artifact isolation verified"
docker exec "$DB_CONTAINER" sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "DELETE FROM decisions WHERE id='"'"'v380-deploy-smoke-decision'"'"'; DELETE FROM decision_projects WHERE id='"'"'v380-deploy-smoke-project'"'"';"' >/dev/null

echo "=== MODULE AUTHORITY BOUNDARIES ==="
mods="$(curl -fsS "http://127.0.0.1:${PORT}/decision-modules")"
python3 - "$mods" <<'PY'
import json,sys
r=json.loads(sys.argv[1])['registry']; mods={m['module_id']:m for m in r['modules']}
assert r['module_count']==4 and set(mods)=={'canvas','finance','narrative-risk','global-impact'},r
for mid in mods:
    assert mods[mid]['status']=='python-domain-authoritative' and mods[mid]['storage_authority']=='python-postgresql',mods[mid]
assert mods['finance']['providers']['compute_authority']=='workbench',mods['finance']
assert mods['global-impact']['providers']['compute_authority']=='workbench',mods['global-impact']
print('PASS: all four Decision Studio domains are authoritative; Workbench retains Finance and Global Impact compute authority')
PY

echo "=== PUBLIC CADDY CHECK ==="
public="$(curl -fsS "$PUBLIC_URL/health")"
python3 - "$public" <<'PY'
import json,sys
x=json.loads(sys.argv[1]); p=x['persistence']; g=x['release']['global_impact']
assert x['version']=='3.8.0' and x['build_fingerprint']=='scds-v3.8.0-global-impact-catalyst-python-domain-migration',x
assert x['global_impact_domain_schema']=='scds-global-impact-domain/1.0',x
assert p['connected'] and p['schema_current'] and p['authority']=='python-postgresql',p
assert p['write_enabled'] is True and p['authority_ready'] is True,p
assert g['status']=='python-domain-authoritative' and g['compute_authority']=='workbench',g
assert g['automatic_impact_verification'] is False and g['automatic_sustainability_rating'] is False,g
print('PASS: public Decision Studio API returns v3.8.0 with authoritative Global Impact Catalyst domain')
PY
curl -fsS "$PUBLIC_URL/global-impact/contract" | python3 -m json.tool

echo "=== FINAL CONTAINERS ==="
docker ps --filter "name=sc-decision-studio" --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
pass "Sustainable Catalyst Decision Studio backend v3.8.0 deployed with Global Impact Catalyst Python domain authority and Workbench compute boundary"
echo "Backup: $backup"
echo "Persistence credentials: $PERSIST_ENV (mode 600; do not commit)"
