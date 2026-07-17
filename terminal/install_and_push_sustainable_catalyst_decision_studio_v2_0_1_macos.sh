#!/usr/bin/env bash
set -euo pipefail

VERSION="2.0.1"
PRODUCT="Sustainable Catalyst Decision Studio"
REPOSITORY_NAME="sustainable-catalyst-decision-studio"
RELEASE_ZIP_NAME="sustainable-catalyst-decision-studio-v${VERSION}-repository.zip"
PLUGIN_ZIP_NAME="sustainable-catalyst-decision-studio-plugin-v${VERSION}.zip"
EXPECTED_REMOTE="git@github.com:Content-Catalyst-LLC/sustainable-catalyst-decision-studio.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOWNLOADS_DIR="${HOME}/Downloads"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/scds-v201.XXXXXX")"
STASH_CREATED=0

cleanup() { rm -rf "$TEMP_DIR"; }
trap cleanup EXIT

say() { printf '\n==> %s\n' "$*"; }
fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

find_release_zip() {
  local candidates=(
    "${SCDS_RELEASE_ZIP:-}"
    "$SCRIPT_DIR/$RELEASE_ZIP_NAME"
    "$(cd "$SCRIPT_DIR/.." 2>/dev/null && pwd)/$RELEASE_ZIP_NAME"
    "$DOWNLOADS_DIR/$RELEASE_ZIP_NAME"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    [[ -n "$candidate" && -f "$candidate" ]] && { printf '%s' "$candidate"; return 0; }
  done
  return 1
}

find_repository() {
  local candidates=(
    "${SCDS_REPOSITORY:-}"
    "$DOWNLOADS_DIR/$REPOSITORY_NAME"
    "$HOME/Documents/GitHub/$REPOSITORY_NAME"
    "$HOME/GitHub/$REPOSITORY_NAME"
    "$PWD"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    [[ -n "$candidate" && -d "$candidate/.git" ]] && { printf '%s' "$candidate"; return 0; }
  done
  return 1
}

find_python() {
  local candidates=(
    "${PYTHON_BIN:-}"
    "/opt/homebrew/bin/python3.13"
    "/opt/homebrew/bin/python3.12"
    "/usr/local/bin/python3.13"
    "/usr/local/bin/python3.12"
    "$(command -v python3 2>/dev/null || true)"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    [[ -n "$candidate" && -x "$candidate" ]] || continue
    "$candidate" - <<'PY' >/dev/null 2>&1 && { printf '%s' "$candidate"; return 0; }
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
  done
  return 1
}

say "Preparing ${PRODUCT} v${VERSION}"
RELEASE_ZIP="$(find_release_zip)" || fail "Could not find $RELEASE_ZIP_NAME. Keep this installer beside the release ZIP or place both in Downloads."
REPOSITORY="$(find_repository)" || fail "Could not find the local Git repository. Set SCDS_REPOSITORY=/absolute/path/to/$REPOSITORY_NAME and run again."
PYTHON="$(find_python)" || fail "Python 3.11 or newer is required. Set PYTHON_BIN to a compatible interpreter."
BRANCH="$(git -C "$REPOSITORY" branch --show-current)"
[[ -n "$BRANCH" ]] || fail "The repository is in detached HEAD state. Check out the intended branch first."
REMOTE_URL="$(git -C "$REPOSITORY" remote get-url origin 2>/dev/null || true)"

printf 'Release ZIP: %s\n' "$RELEASE_ZIP"
printf 'Git repository: %s\n' "$REPOSITORY"
printf 'Python: %s\n' "$PYTHON"
printf 'Branch: %s\n' "$BRANCH"
printf 'Remote: %s\n' "${REMOTE_URL:-not configured}"
if [[ -n "$REMOTE_URL" && "$REMOTE_URL" != "$EXPECTED_REMOTE" ]]; then
  printf 'WARNING: origin differs from the expected repository: %s\n' "$EXPECTED_REMOTE"
fi

say "Creating safety backup"
BACKUP="$DOWNLOADS_DIR/${REPOSITORY_NAME}-before-v${VERSION}-${TIMESTAMP}.zip"
/usr/bin/ditto -c -k --sequesterRsrc --keepParent "$REPOSITORY" "$BACKUP"
printf 'Safety backup: %s\n' "$BACKUP"

if [[ -n "$(git -C "$REPOSITORY" status --porcelain)" ]]; then
  say "Preserving existing uncommitted work"
  git -C "$REPOSITORY" stash push --include-untracked -m "pre-v${VERSION}-${TIMESTAMP}" >/dev/null
  STASH_CREATED=1
  printf 'Existing work was preserved in a Git stash named pre-v%s-%s.\n' "$VERSION" "$TIMESTAMP"
fi

say "Extracting release repository"
unzip -q "$RELEASE_ZIP" -d "$TEMP_DIR/release"
SOURCE_ROOT="$(find "$TEMP_DIR/release" -mindepth 1 -maxdepth 2 -type f -name README.md -print -quit | xargs -I{} dirname "{}")"
[[ -n "$SOURCE_ROOT" && -f "$SOURCE_ROOT/README.md" ]] || fail "The release ZIP does not contain a valid repository root."

say "Installing v${VERSION} source"
rsync -a --delete \
  --exclude='.git/' \
  --exclude='.DS_Store' \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  "$SOURCE_ROOT/" "$REPOSITORY/"

say "Running release validation"
cd "$REPOSITORY"
"$PYTHON" scripts/test_release.py
"$PYTHON" -m pytest backend/tests -q
if command -v php >/dev/null 2>&1; then
  php -l wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php
else
  printf 'INFO: PHP is unavailable; PHP syntax validation was skipped.\n'
fi
if command -v node >/dev/null 2>&1; then
  node --check wordpress-plugin/sustainable-catalyst-decision-studio/assets/js/scds-decision-studio.js
else
  printf 'INFO: Node is unavailable; JavaScript syntax validation was skipped.\n'
fi

say "Building distributable ZIPs"
DIST_DIR="$TEMP_DIR/dist"
bash scripts/build_release.sh "$DIST_DIR"
cp "$DIST_DIR/$PLUGIN_ZIP_NAME" "$DOWNLOADS_DIR/$PLUGIN_ZIP_NAME"
printf 'WordPress plugin ZIP: %s\n' "$DOWNLOADS_DIR/$PLUGIN_ZIP_NAME"

say "Committing release"
git add -A
if git diff --cached --quiet; then
  printf 'INFO: Repository already matches v%s; no commit was needed.\n' "$VERSION"
else
  git commit -m "Decision Studio v${VERSION} — Catalyst Module Navigation and Handoff Repair"
fi

if ! git rev-parse "v${VERSION}" >/dev/null 2>&1; then
  git tag -a "v${VERSION}" -m "Decision Studio v${VERSION} — Catalyst Module Navigation and Handoff Repair"
else
  printf 'INFO: Tag v%s already exists.\n' "$VERSION"
fi

if [[ "${SCDS_NO_PUSH:-0}" == "1" ]]; then
  say "Push skipped because SCDS_NO_PUSH=1"
elif [[ -z "$REMOTE_URL" ]]; then
  say "Push skipped because origin is not configured"
else
  say "Pushing branch and release tag"
  git push origin "$BRANCH"
  git push origin "v${VERSION}"
fi

say "Release complete"
printf '%s v%s is installed in %s.\n' "$PRODUCT" "$VERSION" "$REPOSITORY"
printf 'Upload this plugin ZIP in WordPress: %s\n' "$DOWNLOADS_DIR/$PLUGIN_ZIP_NAME"
if [[ "$STASH_CREATED" == "1" ]]; then
  printf 'Your earlier uncommitted work remains preserved in Git stash. Review it with: git -C %q stash list\n' "$REPOSITORY"
fi
