#!/usr/bin/env python3
"""Validate the supported Home Assistant version across repository metadata."""

from __future__ import annotations

import json
import re
from pathlib import Path

SUPPORTED_VERSION = "2026.7.0"

hacs = json.loads(Path("hacs.json").read_text(encoding="utf-8"))
if hacs.get("homeassistant") != SUPPORTED_VERSION:
    raise SystemExit(f"hacs.json must declare Home Assistant {SUPPORTED_VERSION}")

requirements = Path("requirements-dev.in").read_text(encoding="utf-8")
match = re.search(r"^homeassistant==([^\s]+)$", requirements, re.MULTILINE)
if match is None or match.group(1) != SUPPORTED_VERSION:
    raise SystemExit(
        f"requirements-dev.in must pin Home Assistant {SUPPORTED_VERSION}"
    )

documentation = Path("docs/compatibility.md").read_text(encoding="utf-8")
if f"Home Assistant {SUPPORTED_VERSION} or newer" not in documentation:
    raise SystemExit("Compatibility documentation is out of sync")

print(f"Supported Home Assistant version is consistent: {SUPPORTED_VERSION}")
