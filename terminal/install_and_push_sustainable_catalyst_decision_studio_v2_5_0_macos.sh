#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="2.5.0"
BASE_TAG="v2.4.0"
BASE_TARGET="e32be572c675678baa60061f27d35f9e12d64528"
PREVIOUS_TAG="v2.3.1"
PREVIOUS_TARGET="f93e704da141e6dbc6fe64fff0cede366f1c5542"
ENERGY_TAG="v2.3.0"
ENERGY_TARGET="590e109d9ba85cb9928fda7e44be203504410632"
REPOSITORY_NAME="sustainable-catalyst-decision-studio"
EXPECTED_REMOTE="git@github.com:Content-Catalyst-LLC/sustainable-catalyst-decision-studio.git"
RELEASE_ZIP_NAME="sustainable-catalyst-decision-studio-v${VERSION}-repository.zip"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOWNLOADS="$HOME/Downloads"
REPO="${1:-${SCDS_REPOSITORY:-$DOWNLOADS/$REPOSITORY_NAME}}"
STAMP="$(date +%Y%m%d-%H%M%S)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/scds-v250-install.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail(){ echo "ERROR: $*" >&2; exit 1; }
say(){ printf '\n=== %s ===\n' "$*"; }

[[ -d "$REPO/.git" ]] || fail "Not a Git checkout: $REPO"
ZIP="${SCDS_RELEASE_ZIP:-$DOWNLOADS/$RELEASE_ZIP_NAME}"
[[ -f "$ZIP" ]] || ZIP="$SCRIPT_DIR/$RELEASE_ZIP_NAME"
[[ -f "$ZIP" ]] || fail "Cannot find $RELEASE_ZIP_NAME"
BRANCH="$(git -C "$REPO" branch --show-current)"
[[ "$BRANCH" == "main" ]] || fail "Expected main branch; found ${BRANCH:-detached}"
REMOTE="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
[[ -z "$REMOTE" || "$REMOTE" == "$EXPECTED_REMOTE" ]] || echo "WARNING: origin is $REMOTE"

say "FETCHING GITHUB"
git -C "$REPO" fetch origin --prune --tags
REMOTE_HEAD="$(git -C "$REPO" rev-parse origin/main)"
LOCAL_HEAD="$(git -C "$REPO" rev-parse HEAD)"

say "SAFETY BACKUP"
BACKUP="$DOWNLOADS/${REPOSITORY_NAME}-before-v${VERSION}-${STAMP}.zip"
/usr/bin/ditto -c -k --sequesterRsrc --keepParent "$REPO" "$BACKUP"
echo "$BACKUP"

if [[ -n "$(git -C "$REPO" status --porcelain)" ]]; then
  say "PRESERVING UNCOMMITTED WORK"
  git -C "$REPO" stash push --include-untracked -m "pre-v${VERSION}-${STAMP}"
fi

say "SYNCHRONIZING MAIN"
if [[ "$LOCAL_HEAD" != "$REMOTE_HEAD" ]]; then
  if git -C "$REPO" merge-base --is-ancestor "$LOCAL_HEAD" "$REMOTE_HEAD"; then
    git -C "$REPO" merge --ff-only origin/main
  elif git -C "$REPO" merge-base --is-ancestor "$REMOTE_HEAD" "$LOCAL_HEAD"; then
    RECOVERY_BRANCH="recovery/pre-v${VERSION}-${STAMP}"
    git -C "$REPO" branch "$RECOVERY_BRANCH" "$LOCAL_HEAD"
    echo "Preserved local-only history on $RECOVERY_BRANCH"
    git -C "$REPO" reset --hard "$REMOTE_HEAD"
  else
    fail "Local main and origin/main have diverged. Backup exists at $BACKUP; no history was rewritten."
  fi
fi

BASE_SHA="$(git -C "$REPO" rev-parse "${BASE_TAG}^{}" 2>/dev/null || true)"
[[ "$BASE_SHA" == "$BASE_TARGET" ]] || fail "$BASE_TAG must resolve to canonical v2.4.0 commit $BASE_TARGET; found ${BASE_SHA:-missing}"
PREVIOUS_SHA="$(git -C "$REPO" rev-parse "${PREVIOUS_TAG}^{}" 2>/dev/null || true)"
[[ "$PREVIOUS_SHA" == "$PREVIOUS_TARGET" ]] || fail "$PREVIOUS_TAG must remain at $PREVIOUS_TARGET; found ${PREVIOUS_SHA:-missing}"
git -C "$REPO" merge-base --is-ancestor "$BASE_SHA" HEAD || fail "Current main does not contain $BASE_TAG"
ENERGY_SHA="$(git -C "$REPO" rev-parse "${ENERGY_TAG}^{}" 2>/dev/null || true)"
[[ "$ENERGY_SHA" == "$ENERGY_TARGET" ]] || fail "$ENERGY_TAG must remain at Energy Runtime Consumer commit $ENERGY_TARGET; found ${ENERGY_SHA:-missing}"
[[ -f "$REPO/backend/app/energy_runtime_consumer.py" ]] || fail "Energy Runtime Consumer is missing before v2.5.0 install"

say "INSTALLING v2.5.0 RELEASE"
unzip -q "$ZIP" -d "$TMP/release"
SRC="$(find "$TMP/release" -mindepth 1 -maxdepth 3 -type f -name README.md -print -quit | xargs -I{} dirname "{}")"
[[ -n "$SRC" && -f "$SRC/backend/app/scenario_stress.py" && -f "$SRC/backend/app/uncertainty_confidence.py" && -f "$SRC/backend/app/tradeoff_matrix.py" && -f "$SRC/backend/app/energy_runtime_consumer.py" ]] || fail "v2.5.0 source payload is incomplete"
rsync -a --delete --exclude='.git/' --exclude='.DS_Store' --exclude='__pycache__/' --exclude='.pytest_cache/' "$SRC/" "$REPO/"

say "SELECTING PYTHON 3.12/3.13"
PY="${PYTHON_BIN:-}"
if [[ -z "$PY" ]]; then
  for c in /opt/homebrew/bin/python3.13 /usr/local/bin/python3.13 /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12; do
    [[ -x "$c" ]] && { PY="$c"; break; }
  done
fi
[[ -n "$PY" ]] || fail "Python 3.12 or 3.13 is required; do not use Python 3.14 with the pinned pydantic-core."
"$PY" - <<'PY'
import sys
raise SystemExit(0 if (3,12) <= sys.version_info[:2] <= (3,13) else 1)
PY
"$PY" --version

say "VALIDATING SCENARIO COMPARISON + STRESS TESTING"
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

say "BUILDING DISTRIBUTABLES"
DIST="$TMP/dist"
PYTHON_BIN="$VENV/bin/python" bash scripts/build_release.sh "$DIST"
cp "$DIST/sustainable-catalyst-decision-studio-plugin-v${VERSION}.zip" "$DOWNLOADS/"
cp "$DIST/sustainable-catalyst-decision-studio-backend-v${VERSION}.zip" "$DOWNLOADS/"
cp "$DIST/sustainable-catalyst-decision-studio-v${VERSION}-repository.zip" "$DOWNLOADS/"
cp "$REPO/deploy/contabo/upgrade_decision_studio_backend_v2_5_0_contabo.sh" "$DOWNLOADS/"
cp "$REPO/deploy/contabo/deploy_decision_studio_v2_5_0_from_macos.sh" "$DOWNLOADS/"
chmod +x "$DOWNLOADS/upgrade_decision_studio_backend_v2_5_0_contabo.sh" "$DOWNLOADS/deploy_decision_studio_v2_5_0_from_macos.sh"

say "COMMIT v2.5.0"
git add -A
if git diff --cached --quiet; then
  echo "Repository already matches v2.5.0."
else
  git commit -m "Decision Studio v2.5.0 — Scenario Comparison & Stress Testing"
fi
HEAD_SHA="$(git rev-parse HEAD)"

say "TAG v2.5.0"
if git rev-parse 'v2.5.0^{}' >/dev/null 2>&1; then
  EXISTING="$(git rev-parse 'v2.5.0^{}')"
  [[ "$EXISTING" == "$HEAD_SHA" ]] || fail "Existing v2.5.0 tag points to $EXISTING, not current HEAD $HEAD_SHA"
else
  git tag -a v2.5.0 -m "Decision Studio v2.5.0 — Scenario Comparison & Stress Testing"
fi

if [[ "${SCDS_NO_PUSH:-0}" != "1" && -n "$REMOTE" ]]; then
  say "PUSHING GITHUB"
  git push origin main
  git push origin v2.5.0
fi

say "FINAL GITHUB VERIFICATION"
git fetch origin --prune --tags
HEAD_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse origin/main)"
TAG_SHA="$(git rev-parse 'v2.5.0^{}')"
BASE_AFTER="$(git rev-parse 'v2.4.0^{}')"
PREVIOUS_AFTER="$(git rev-parse 'v2.3.1^{}')"
ENERGY_AFTER="$(git rev-parse 'v2.3.0^{}')"
printf 'HEAD:       %s\norigin/main:%s\nv2.5.0:     %s\nv2.4.0:     %s\nv2.3.1:     %s\nv2.3.0:     %s\n' "$HEAD_SHA" "$REMOTE_SHA" "$TAG_SHA" "$BASE_AFTER" "$PREVIOUS_AFTER" "$ENERGY_AFTER"
[[ "$HEAD_SHA" == "$REMOTE_SHA" && "$HEAD_SHA" == "$TAG_SHA" ]] || fail "v2.5.0 GitHub alignment failed"
[[ "$BASE_AFTER" == "$BASE_TARGET" ]] || fail "v2.4.0 tag moved unexpectedly"
[[ "$PREVIOUS_AFTER" == "$PREVIOUS_TARGET" ]] || fail "v2.3.1 tag moved unexpectedly"
[[ "$ENERGY_AFTER" == "$ENERGY_TARGET" ]] || fail "v2.3.0 Energy tag moved unexpectedly"
[[ -z "$(git status --porcelain)" ]] || fail "Working tree is not clean after v2.5.0"
echo "PASS: Decision Studio v2.5.0 is aligned; v2.4.0, v2.3.1, and Energy v2.3.0 history remain intact."
echo "WordPress ZIP: $DOWNLOADS/sustainable-catalyst-decision-studio-plugin-v${VERSION}.zip"
echo "Backend ZIP:   $DOWNLOADS/sustainable-catalyst-decision-studio-backend-v${VERSION}.zip"
echo "VPS deploy:    $DOWNLOADS/deploy_decision_studio_v2_5_0_from_macos.sh"
