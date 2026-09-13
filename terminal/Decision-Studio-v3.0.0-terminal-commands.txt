#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="3.0.0"
BASE_TAG="v2.9.0"
REPOSITORY_NAME="sustainable-catalyst-decision-studio"
EXPECTED_REMOTE="git@github.com:Content-Catalyst-LLC/sustainable-catalyst-decision-studio.git"
OVERLAY_ZIP_NAME="sustainable-catalyst-decision-studio-v${VERSION}-overlay.zip"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOWNLOADS="$HOME/Downloads"
REPO="${1:-${SCDS_REPOSITORY:-$DOWNLOADS/$REPOSITORY_NAME}}"
STAMP="$(date +%Y%m%d-%H%M%S)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/scds-v300-install.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }
say(){ printf '\n=== %s ===\n' "$*"; }
[[ -d "$REPO/.git" ]] || fail "Not a Git checkout: $REPO"
OVERLAY="${SCDS_RELEASE_OVERLAY:-$DOWNLOADS/$OVERLAY_ZIP_NAME}"
[[ -f "$OVERLAY" ]] || OVERLAY="$SCRIPT_DIR/$OVERLAY_ZIP_NAME"
[[ -f "$OVERLAY" ]] || fail "Cannot find $OVERLAY_ZIP_NAME"
[[ "$(git -C "$REPO" branch --show-current)" == "main" ]] || fail "Expected main branch"
REMOTE="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
[[ -z "$REMOTE" || "$REMOTE" == "$EXPECTED_REMOTE" ]] || echo "WARNING: origin is $REMOTE"
say "FETCHING GITHUB"
git -C "$REPO" fetch origin --prune --tags
say "SAFETY BACKUP"
BACKUP="$DOWNLOADS/${REPOSITORY_NAME}-before-v${VERSION}-${STAMP}.zip"
/usr/bin/ditto -c -k --sequesterRsrc --keepParent "$REPO" "$BACKUP"
echo "$BACKUP"
if [[ -n "$(git -C "$REPO" status --porcelain)" ]]; then
  say "PRESERVING UNCOMMITTED WORK"
  git -C "$REPO" stash push --include-untracked -m "pre-v${VERSION}-${STAMP}"
fi
say "VERIFYING CANONICAL v2.9.0 BASE"
BASE_SHA="$(git -C "$REPO" rev-parse "${BASE_TAG}^{}" 2>/dev/null || true)"
[[ -n "$BASE_SHA" ]] || fail "v2.9.0 is not installed/tagged yet. Close v2.9.0 before applying v3.0.0."
LOCAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"
REMOTE_HEAD="$(git -C "$REPO" rev-parse origin/main)"
[[ "$LOCAL_HEAD" == "$REMOTE_HEAD" ]] || fail "Local main and origin/main differ. Reconcile before v3.0.0. Backup: $BACKUP"
[[ "$LOCAL_HEAD" == "$BASE_SHA" ]] || fail "v3.0.0 must start from exact v2.9.0. HEAD=$LOCAL_HEAD v2.9.0=$BASE_SHA"
if git -C "$REPO" rev-parse 'v3.0.0^{}' >/dev/null 2>&1; then fail "v3.0.0 tag already exists; installer never rewrites published tags."; fi
# Snapshot all published historical v2 tags to prove they do not move.
HISTORY_BEFORE="$TMP/history-before.txt"
for tag in v2.9.0 v2.8.0 v2.7.0 v2.6.0 v2.5.0 v2.4.0 v2.3.1 v2.3.0; do
  sha="$(git -C "$REPO" rev-parse "${tag}^{}" 2>/dev/null || true)"
  [[ -n "$sha" ]] || fail "Historical tag missing: $tag"
  printf '%s %s\n' "$tag" "$sha" >> "$HISTORY_BEFORE"
done
[[ -f "$REPO/backend/app/recommendation_review.py" ]] || fail "v2.9 recommendation review module missing"
[[ -f "$REPO/backend/app/dependency_graph.py" ]] || fail "v2.8 dependency graph module missing"
[[ -f "$REPO/backend/app/site_intelligence_context.py" ]] || fail "v2.7 Site Intelligence context module missing"
[[ -f "$REPO/backend/app/native_handoffs.py" ]] || fail "v2.6 native handoff module missing"
say "APPLYING v3.0.0 ADDITIVE OVERLAY"
unzip -q "$OVERLAY" -d "$TMP/overlay"
SRC="$(find "$TMP/overlay" -mindepth 1 -maxdepth 2 -type d -name 'sustainable-catalyst-decision-studio-v3.0.0-overlay' -print -quit)"
[[ -n "$SRC" ]] || fail "Could not locate v3.0.0 overlay root"
for required in \
  backend/app/connected_decision_intelligence.py \
  backend/app/main.py \
  backend/tests/test_backend.py \
  data/connected_decision_intelligence_contract_v3.0.0.json \
  data/decision_lifecycle_state_contract_v3.0.0.json \
  data/decision_readiness_matrix_contract_v3.0.0.json \
  data/cross_product_route_plan_contract_v3.0.0.json \
  deploy/contabo/upgrade_decision_studio_backend_v3_0_0_contabo.sh \
  wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php; do
  [[ -f "$SRC/$required" ]] || fail "v3.0.0 overlay missing $required"
done
rsync -a --exclude='.DS_Store' --exclude='__pycache__/' --exclude='.pytest_cache/' "$SRC/" "$REPO/"
say "SELECTING PYTHON 3.12/3.13"
PY="${PYTHON_BIN:-}"
if [[ -z "$PY" ]]; then
  for c in /opt/homebrew/bin/python3.13 /usr/local/bin/python3.13 /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12; do
    [[ -x "$c" ]] && { PY="$c"; break; }
  done
fi
[[ -n "$PY" ]] || fail "Python 3.12 or 3.13 is required"
"$PY" - <<'PY'
import sys
raise SystemExit(0 if (3,12) <= sys.version_info[:2] <= (3,13) else 1)
PY
"$PY" --version
say "VALIDATING CONNECTED DECISION INTELLIGENCE"
VENV="$TMP/venv"
"$PY" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV/bin/python" -m pip install -r "$REPO/backend/requirements.txt" >/dev/null
cd "$REPO"
"$VENV/bin/python" scripts/test_release.py
"$VENV/bin/python" -m pytest backend/tests -q
php -l wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php
if command -v node >/dev/null 2>&1; then
  node --check wordpress-plugin/sustainable-catalyst-decision-studio/assets/js/scds-decision-studio.js
  node --check wordpress-plugin/sustainable-catalyst-decision-studio/assets/js/scds-offline-workspace.js
fi
bash -n deploy/contabo/upgrade_decision_studio_backend_v3_0_0_contabo.sh
bash -n deploy/contabo/deploy_decision_studio_v3_0_0_from_macos.sh
say "BUILDING DISTRIBUTABLES"
DIST="$TMP/dist"
PYTHON_BIN="$VENV/bin/python" bash scripts/build_release.sh "$DIST"
cp "$DIST/sustainable-catalyst-decision-studio-plugin-v${VERSION}.zip" "$DOWNLOADS/"
cp "$DIST/sustainable-catalyst-decision-studio-backend-v${VERSION}.zip" "$DOWNLOADS/"
cp "$DIST/sustainable-catalyst-decision-studio-v${VERSION}-repository.zip" "$DOWNLOADS/"
cp deploy/contabo/upgrade_decision_studio_backend_v3_0_0_contabo.sh "$DOWNLOADS/"
cp deploy/contabo/deploy_decision_studio_v3_0_0_from_macos.sh "$DOWNLOADS/"
chmod +x "$DOWNLOADS/upgrade_decision_studio_backend_v3_0_0_contabo.sh" "$DOWNLOADS/deploy_decision_studio_v3_0_0_from_macos.sh"
say "COMMIT v3.0.0"
git add -A
git diff --cached --quiet && fail "No v3.0.0 changes detected"
git commit -m "Decision Studio v3.0.0 — Connected Decision Intelligence"
HEAD_SHA="$(git rev-parse HEAD)"
say "TAG v3.0.0"
git tag -a v3.0.0 -m "Decision Studio v3.0.0 — Connected Decision Intelligence"
if [[ "${SCDS_NO_PUSH:-0}" != "1" && -n "$REMOTE" ]]; then
  say "PUSHING GITHUB"
  git push origin main
  git push origin v3.0.0
fi
say "FINAL GITHUB VERIFICATION"
git fetch origin --prune --tags
REMOTE_SHA="$(git rev-parse origin/main)"
TAG_SHA="$(git rev-parse 'v3.0.0^{}')"
printf 'HEAD:       %s\norigin/main:%s\nv3.0.0:     %s\nv2.9.0:     %s\n' "$HEAD_SHA" "$REMOTE_SHA" "$TAG_SHA" "$BASE_SHA"
[[ "$HEAD_SHA" == "$REMOTE_SHA" && "$HEAD_SHA" == "$TAG_SHA" ]] || fail "v3.0.0 GitHub alignment failed"
HISTORY_AFTER="$TMP/history-after.txt"
while read -r tag before; do
  after="$(git rev-parse "${tag}^{}")"
  printf '%s %s\n' "$tag" "$after" >> "$HISTORY_AFTER"
  [[ "$before" == "$after" ]] || fail "Historical tag moved unexpectedly: $tag"
done < "$HISTORY_BEFORE"
[[ -z "$(git status --porcelain)" ]] || fail "Working tree is not clean"
echo "PASS: Decision Studio v3.0.0 aligned; all v2 historical tags remain intact."
echo "WordPress ZIP: $DOWNLOADS/sustainable-catalyst-decision-studio-plugin-v${VERSION}.zip"
echo "Backend ZIP:   $DOWNLOADS/sustainable-catalyst-decision-studio-backend-v${VERSION}.zip"
echo "VPS deploy:    $DOWNLOADS/deploy_decision_studio_v3_0_0_from_macos.sh"
