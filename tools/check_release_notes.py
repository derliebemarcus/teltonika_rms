#!/usr/bin/env python3
"""Validate changelog release-note headings for the current manifest version."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED_HEADINGS = (
    "### New Features",
    "### Improvements",
    "### Changes",
    "### Bugfixes",
)


def extract_section(changelog: str, version: str) -> str:
    lines = changelog.splitlines()
    capture = False
    collected: list[str] = []
    for line in lines:
        if line.startswith(f"## {version} - "):
            capture = True
            continue
        if capture and line.startswith("## "):
            break
        if capture:
            collected.append(line)
    return "\n".join(collected).strip()


def main() -> int:
    manifest_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("manifest.json")
    changelog_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("CHANGELOG.md")

    version = str(json.loads(manifest_path.read_text(encoding="utf-8"))["version"]).strip()
    section = extract_section(changelog_path.read_text(encoding="utf-8"), version)
    if not section:
        print(f"Missing changelog section for version {version}")
        return 1
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in section]
    if missing:
        print(f"Version {version} is missing release-note headings: {', '.join(missing)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
