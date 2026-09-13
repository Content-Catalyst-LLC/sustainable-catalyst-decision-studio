#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="2.8.0"
BASE_TAG="v2.7.0"
V260_TAG="v2.6.0"; V260_TARGET="c37f99c3ec6aaf66df55d1d47991a6df5647d986"
V250_TAG="v2.5.0"; V250_TARGET="489c2c04d2fe8042762c5f796c0c9b71141bc7cc"
V240_TAG="v2.4.0"; V240_TARGET="e32be572c675678baa60061f27d35f9e12d64528"
V231_TAG="v2.3.1"; V231_TARGET="f93e704da141e6dbc6fe64fff0cede366f1c5542"
ENERGY_TAG="v2.3.0"; ENERGY_TARGET="590e109d9ba85cb9928fda7e44be203504410632"
REPOSITORY_NAME="sustainable-catalyst-decision-studio"
EXPECTED_REMOTE="git@github.com:Content-Catalyst-LLC/sustainable-catalyst-decision-studio.git"
OVERLAY_ZIP_NAME="sustainable-catalyst-decision-studio-v${VERSION}-overlay.zip"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOWNLOADS="$HOME/Downloads"
REPO="${1:-${SCDS_REPOSITORY:-$DOWNLOADS/$REPOSITORY_NAME}}"
STAMP="$(date +%Y%m%d-%H%M%S)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/scds-v280-install.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }
say(){ printf '\n=== %s ===\n' "$*"; }
[[ -d "$REPO/.git" ]] || fail "Not a Git checkout: $REPO"
OVERLAY="${SCDS_RELEASE_OVERLAY:-$DOWNLOADS/$OVERLAY_ZIP_NAME}"; [[ -f "$OVERLAY" ]] || OVERLAY="$SCRIPT_DIR/$OVERLAY_ZIP_NAME"; [[ -f "$OVERLAY" ]] || fail "Cannot find $OVERLAY_ZIP_NAME"
[[ "$(git -C "$REPO" branch --show-current)" == "main" ]] || fail "Expected main branch"
REMOTE="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"; [[ -z "$REMOTE" || "$REMOTE" == "$EXPECTED_REMOTE" ]] || echo "WARNING: origin is $REMOTE"
say "FETCHING GITHUB"; git -C "$REPO" fetch origin --prune --tags
say "SAFETY BACKUP"; BACKUP="$DOWNLOADS/${REPOSITORY_NAME}-before-v${VERSION}-${STAMP}.zip"; /usr/bin/ditto -c -k --sequesterRsrc --keepParent "$REPO" "$BACKUP"; echo "$BACKUP"
if [[ -n "$(git -C "$REPO" status --porcelain)" ]]; then say "PRESERVING UNCOMMITTED WORK"; git -C "$REPO" stash push --include-untracked -m "pre-v${VERSION}-${STAMP}"; fi
say "SYNCHRONIZING MAIN"
LOCAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"; REMOTE_HEAD="$(git -C "$REPO" rev-parse origin/main)"
if [[ "$LOCAL_HEAD" != "$REMOTE_HEAD" ]]; then
  if git -C "$REPO" merge-base --is-ancestor "$LOCAL_HEAD" "$REMOTE_HEAD"; then git -C "$REPO" merge --ff-only origin/main
  elif git -C "$REPO" merge-base --is-ancestor "$REMOTE_HEAD" "$LOCAL_HEAD"; then RECOVERY="recovery/pre-v${VERSION}-${STAMP}"; git -C "$REPO" branch "$RECOVERY" "$LOCAL_HEAD"; echo "Preserved local-only history on $RECOVERY"; git -C "$REPO" reset --hard "$REMOTE_HEAD"
  else fail "Local main and origin/main have diverged. Backup exists at $BACKUP; no history was rewritten."; fi
fi
BASE_SHA="$(git -C "$REPO" rev-parse "${BASE_TAG}^{}" 2>/dev/null || true)"; [[ -n "$BASE_SHA" ]] || fail "v2.7.0 is not installed/tagged yet. Close v2.7.0 before applying v2.8.0."
[[ "$(git -C "$REPO" rev-parse HEAD)" == "$BASE_SHA" ]] || fail "v2.8.0 must start from the exact v2.7.0 tag. Current HEAD differs from $BASE_TAG."
[[ "$(git -C "$REPO" rev-parse "${V260_TAG}^{}")" == "$V260_TARGET" ]] || fail "v2.6.0 historical tag moved"
[[ "$(git -C "$REPO" rev-parse "${V250_TAG}^{}")" == "$V250_TARGET" ]] || fail "v2.5.0 historical tag moved"
[[ "$(git -C "$REPO" rev-parse "${V240_TAG}^{}")" == "$V240_TARGET" ]] || fail "v2.4.0 historical tag moved"
[[ "$(git -C "$REPO" rev-parse "${V231_TAG}^{}")" == "$V231_TARGET" ]] || fail "v2.3.1 historical tag moved"
[[ "$(git -C "$REPO" rev-parse "${ENERGY_TAG}^{}")" == "$ENERGY_TARGET" ]] || fail "v2.3.0 Energy historical tag moved"
[[ -f "$REPO/backend/app/site_intelligence_context.py" ]] || fail "v2.7 Site Intelligence context module missing"
[[ -f "$REPO/backend/app/native_handoffs.py" ]] || fail "v2.6 native handoff module missing"
if git -C "$REPO" rev-parse 'v2.8.0^{}' >/dev/null 2>&1; then fail "v2.8.0 tag already exists; installer never rewrites published tags."; fi
say "APPLYING v2.8.0 ADDITIVE OVERLAY"
unzip -q "$OVERLAY" -d "$TMP/overlay"
SRC="$(find "$TMP/overlay" -mindepth 1 -maxdepth 2 -type d -name 'sustainable-catalyst-decision-studio-v2.8.0-overlay' -print -quit)"; [[ -n "$SRC" ]] || fail "Could not locate v2.8.0 overlay root"
for required in backend/app/dependency_graph.py backend/app/main.py backend/tests/test_backend.py data/decision_dependency_graph_contract_v2.8.0.json data/dependency_diagnostics_contract_v2.8.0.json data/change_impact_assessment_contract_v2.8.0.json deploy/contabo/upgrade_decision_studio_backend_v2_8_0_contabo.sh wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php; do [[ -f "$SRC/$required" ]] || fail "v2.8.0 overlay missing $required"; done
rsync -a --exclude='.DS_Store' --exclude='__pycache__/' --exclude='.pytest_cache/' "$SRC/" "$REPO/"
say "SELECTING PYTHON 3.12/3.13"
PY="${PYTHON_BIN:-}"; if [[ -z "$PY" ]]; then for c in /opt/homebrew/bin/python3.13 /usr/local/bin/python3.13 /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12; do [[ -x "$c" ]] && { PY="$c"; break; }; done; fi
[[ -n "$PY" ]] || fail "Python 3.12 or 3.13 is required"
"$PY" - <<'PY'
import sys
raise SystemExit(0 if (3,12) <= sys.version_info[:2] <= (3,13) else 1)
PY
"$PY" --version
say "VALIDATING DECISION GRAPH & DEPENDENCY MAPPING"
VENV="$TMP/venv"; "$PY" -m venv "$VENV"; "$VENV/bin/python" -m pip install --upgrade pip >/dev/null; "$VENV/bin/python" -m pip install -r "$REPO/backend/requirements.txt" >/dev/null
cd "$REPO"; "$VENV/bin/python" scripts/test_release.py; "$VENV/bin/python" -m pytest backend/tests -q
php -l wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php
if command -v node >/dev/null 2>&1; then node --check wordpress-plugin/sustainable-catalyst-decision-studio/assets/js/scds-decision-studio.js; node --check wordpress-plugin/sustainable-catalyst-decision-studio/assets/js/scds-offline-workspace.js; fi
bash -n deploy/contabo/upgrade_decision_studio_backend_v2_8_0_contabo.sh; bash -n deploy/contabo/deploy_decision_studio_v2_8_0_from_macos.sh
say "BUILDING DISTRIBUTABLES"
DIST="$TMP/dist"; PYTHON_BIN="$VENV/bin/python" bash scripts/build_release.sh "$DIST"
cp "$DIST/sustainable-catalyst-decision-studio-plugin-v${VERSION}.zip" "$DOWNLOADS/"; cp "$DIST/sustainable-catalyst-decision-studio-backend-v${VERSION}.zip" "$DOWNLOADS/"; cp "$DIST/sustainable-catalyst-decision-studio-v${VERSION}-repository.zip" "$DOWNLOADS/"
cp deploy/contabo/upgrade_decision_studio_backend_v2_8_0_contabo.sh "$DOWNLOADS/"; cp deploy/contabo/deploy_decision_studio_v2_8_0_from_macos.sh "$DOWNLOADS/"; chmod +x "$DOWNLOADS/"*decision_studio*v2_8_0*.sh 2>/dev/null || true
say "COMMIT v2.8.0"; git add -A; git diff --cached --quiet && fail "No v2.8.0 changes detected"; git commit -m "Decision Studio v2.8.0 — Decision Graph & Dependency Mapping"
HEAD_SHA="$(git rev-parse HEAD)"; say "TAG v2.8.0"; git tag -a v2.8.0 -m "Decision Studio v2.8.0 — Decision Graph & Dependency Mapping"
if [[ "${SCDS_NO_PUSH:-0}" != "1" && -n "$REMOTE" ]]; then say "PUSHING GITHUB"; git push origin main; git push origin v2.8.0; fi
say "FINAL GITHUB VERIFICATION"; git fetch origin --prune --tags
REMOTE_SHA="$(git rev-parse origin/main)"; TAG_SHA="$(git rev-parse 'v2.8.0^{}')"; BASE_AFTER="$(git rev-parse 'v2.7.0^{}')"
printf 'HEAD:       %s\norigin/main:%s\nv2.8.0:     %s\nv2.7.0:     %s\n' "$HEAD_SHA" "$REMOTE_SHA" "$TAG_SHA" "$BASE_AFTER"
[[ "$HEAD_SHA" == "$REMOTE_SHA" && "$HEAD_SHA" == "$TAG_SHA" ]] || fail "v2.8.0 GitHub alignment failed"
[[ "$BASE_AFTER" == "$BASE_SHA" ]] || fail "v2.7.0 tag moved unexpectedly"
[[ "$(git rev-parse 'v2.6.0^{}')" == "$V260_TARGET" && "$(git rev-parse 'v2.5.0^{}')" == "$V250_TARGET" && "$(git rev-parse 'v2.4.0^{}')" == "$V240_TARGET" && "$(git rev-parse 'v2.3.1^{}')" == "$V231_TARGET" && "$(git rev-parse 'v2.3.0^{}')" == "$ENERGY_TARGET" ]] || fail "Historical tag verification failed"
[[ -z "$(git status --porcelain)" ]] || fail "Working tree is not clean"
echo "PASS: Decision Studio v2.8.0 aligned; v2.7.0 and all historical release tags remain intact."
echo "WordPress ZIP: $DOWNLOADS/sustainable-catalyst-decision-studio-plugin-v${VERSION}.zip"; echo "Backend ZIP: $DOWNLOADS/sustainable-catalyst-decision-studio-backend-v${VERSION}.zip"; echo "VPS deploy: $DOWNLOADS/deploy_decision_studio_v2_8_0_from_macos.sh"
