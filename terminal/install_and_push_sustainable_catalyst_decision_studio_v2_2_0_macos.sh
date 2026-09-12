#!/usr/bin/env bash
set -Eeuo pipefail
VERSION="2.2.0"
REPOSITORY_NAME="sustainable-catalyst-decision-studio"
EXPECTED_REMOTE="git@github.com:Content-Catalyst-LLC/sustainable-catalyst-decision-studio.git"
RELEASE_ZIP_NAME="sustainable-catalyst-decision-studio-v${VERSION}-repository.zip"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOWNLOADS="$HOME/Downloads"
REPO="${1:-${SCDS_REPOSITORY:-$DOWNLOADS/$REPOSITORY_NAME}}"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/scds-v220-install.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
fail(){ echo "ERROR: $*" >&2; exit 1; }
say(){ printf '\n=== %s ===\n' "$*"; }

[[ -d "$REPO/.git" ]] || fail "Not a Git checkout: $REPO"
ZIP="${SCDS_RELEASE_ZIP:-$DOWNLOADS/$RELEASE_ZIP_NAME}"
[[ -f "$ZIP" ]] || ZIP="$SCRIPT_DIR/$RELEASE_ZIP_NAME"
[[ -f "$ZIP" ]] || fail "Cannot find $RELEASE_ZIP_NAME"
BRANCH="$(git -C "$REPO" branch --show-current)"; [[ -n "$BRANCH" ]] || fail "Detached HEAD"
REMOTE="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
[[ -z "$REMOTE" || "$REMOTE" == "$EXPECTED_REMOTE" ]] || echo "WARNING: origin is $REMOTE"

say "SYNCHRONIZING GITHUB MAIN"
git -C "$REPO" fetch origin --prune --tags
if [[ -n "$REMOTE" ]]; then
  git -C "$REPO" merge --ff-only "origin/$BRANCH" || fail "Local and GitHub history diverged. Resolve before applying v2.2.0; no force push was attempted."
fi

say "SAFETY BACKUP"
BACKUP="$DOWNLOADS/${REPOSITORY_NAME}-before-v${VERSION}-$(date +%Y%m%d-%H%M%S).zip"
/usr/bin/ditto -c -k --sequesterRsrc --keepParent "$REPO" "$BACKUP"
echo "$BACKUP"

if [[ -n "$(git -C "$REPO" status --porcelain)" ]]; then
  say "PRESERVING LOCAL CHANGES"
  git -C "$REPO" stash push --include-untracked -m "pre-v${VERSION}-$(date +%Y%m%d-%H%M%S)"
fi

say "INSTALLING v2.2.0"
unzip -q "$ZIP" -d "$TMP/release"
SRC="$(find "$TMP/release" -mindepth 1 -maxdepth 2 -type f -name README.md -print -quit | xargs -I{} dirname "{}")"
[[ -f "$SRC/backend/app/evidence_bundle.py" ]] || fail "v2.2.0 source payload incomplete"
rsync -a --delete --exclude='.git/' --exclude='.DS_Store' --exclude='__pycache__/' --exclude='.pytest_cache/' "$SRC/" "$REPO/"

say "PYTHON 3.13 VALIDATION ENVIRONMENT"
PY="${PYTHON_BIN:-}"
if [[ -z "$PY" ]]; then
  for c in /opt/homebrew/bin/python3.13 /usr/local/bin/python3.13 /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12; do [[ -x "$c" ]] && { PY="$c"; break; }; done
fi
[[ -n "$PY" ]] || fail "Python 3.12 or 3.13 is required for pinned pydantic-core; do not use Python 3.14."
"$PY" - <<'PY' || exit 1
import sys
raise SystemExit(0 if (3,12) <= sys.version_info[:2] <= (3,13) else 1)
PY
VENV="$TMP/venv"
"$PY" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV/bin/python" -m pip install -r "$REPO/backend/requirements.txt" >/dev/null
cd "$REPO"
"$VENV/bin/python" scripts/test_release.py
"$VENV/bin/python" -m pytest backend/tests -q
php -l wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php
command -v node >/dev/null 2>&1 && node --check wordpress-plugin/sustainable-catalyst-decision-studio/assets/js/scds-decision-studio.js

say "BUILDING WORDPRESS + BACKEND DISTRIBUTABLES"
DIST="$TMP/dist"
PYTHON_BIN="$VENV/bin/python" bash scripts/build_release.sh "$DIST"
cp "$DIST/sustainable-catalyst-decision-studio-plugin-v2.2.0.zip" "$DOWNLOADS/"
cp "$DIST/sustainable-catalyst-decision-studio-backend-v2.2.0.zip" "$DOWNLOADS/"
cp "$REPO/deploy/contabo/upgrade_decision_studio_backend_v2_2_0_contabo.sh" "$DOWNLOADS/"
chmod +x "$DOWNLOADS/upgrade_decision_studio_backend_v2_2_0_contabo.sh"

say "COMMIT + PUSH"
git add -A
if ! git diff --cached --quiet; then git commit -m "Decision Studio v2.2.0 — Evidence & Source Bundles"; else echo "Repository already matches v2.2.0."; fi
if git rev-parse 'v2.2.0' >/dev/null 2>&1; then echo "Tag v2.2.0 already exists locally; leaving it unchanged."; else git tag -a v2.2.0 -m "Decision Studio v2.2.0 — Evidence & Source Bundles"; fi
if [[ "${SCDS_NO_PUSH:-0}" != "1" && -n "$REMOTE" ]]; then
  git push origin "$BRANCH"
  git push origin v2.2.0
fi

say "VERIFY"
git fetch origin --prune --tags
HEAD_SHA="$(git rev-parse HEAD)"; REMOTE_SHA="$(git rev-parse "origin/$BRANCH")"
echo "HEAD:        $HEAD_SHA"
echo "origin/$BRANCH: $REMOTE_SHA"
[[ "$HEAD_SHA" == "$REMOTE_SHA" ]] || fail "GitHub branch does not match local HEAD"
echo "PASS: Decision Studio v2.2.0 is committed and on GitHub $BRANCH"
echo "WordPress ZIP: $DOWNLOADS/sustainable-catalyst-decision-studio-plugin-v2.2.0.zip"
echo "Backend ZIP:   $DOWNLOADS/sustainable-catalyst-decision-studio-backend-v2.2.0.zip"
echo "VPS upgrader:  $DOWNLOADS/upgrade_decision_studio_backend_v2_2_0_contabo.sh"
