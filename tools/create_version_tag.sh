#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
MANIFEST="$ROOT/manifest.json"

if [ ! -f "$MANIFEST" ]; then
  echo "manifest.json not found in repository root."
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

if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  echo "Tag $TAG already exists."
  exit 1
fi

git tag -a "$TAG" -m "Release $TAG"
echo "Created tag $TAG"
