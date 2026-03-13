#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
MANIFEST="$ROOT/manifest.json"
CHANGELOG="$ROOT/CHANGELOG.md"

if [ ! -f "$MANIFEST" ]; then
  echo "manifest.json not found in repository root."
  exit 1
fi

if [ ! -f "$CHANGELOG" ]; then
  echo "CHANGELOG.md not found in repository root."
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI ('gh') is required to publish releases."
  exit 1
fi

VERSION="$(
  python3 - "$MANIFEST" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
version = str(manifest.get("version", "")).strip()
print(version)
PY
)"

if [ -z "$VERSION" ]; then
  echo "manifest.json has no version value."
  exit 1
fi

TAG="v$VERSION"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

if [ "$BRANCH" = "HEAD" ]; then
  echo "Detached HEAD is not supported for publishing a release."
  exit 1
fi

if ! git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  "$ROOT/tools/create_version_tag.sh"
fi

TAG_COMMIT="$(git rev-list -n 1 "$TAG")"
if ! git merge-base --is-ancestor "$TAG_COMMIT" HEAD; then
  echo "Tag $TAG is not in current branch history."
  exit 1
fi

RELEASE_NOTES_FILE="$(mktemp "${TMPDIR:-/tmp}/teltonika-rms-release-notes-XXXXXX.md")"
cleanup() {
  rm -f "$RELEASE_NOTES_FILE"
}
trap cleanup EXIT

awk -v version="$VERSION" '
  $0 ~ "^## " version " - " {capture=1; next}
  capture && /^## / {exit}
  capture {print}
' "$CHANGELOG" >"$RELEASE_NOTES_FILE"

if [ ! -s "$RELEASE_NOTES_FILE" ]; then
  echo "Could not extract release notes for version $VERSION from CHANGELOG.md."
  exit 1
fi

git push origin "$BRANCH" --follow-tags

if gh release view "$TAG" >/dev/null 2>&1; then
  gh release edit "$TAG" \
    --title "Release $TAG" \
    --notes-file "$RELEASE_NOTES_FILE"
  echo "Updated GitHub release $TAG"
else
  gh release create "$TAG" \
    --title "Release $TAG" \
    --notes-file "$RELEASE_NOTES_FILE"
  echo "Created GitHub release $TAG"
fi
