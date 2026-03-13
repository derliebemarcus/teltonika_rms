"""Tests for platform registration and entity migration expectations."""

from __future__ import annotations

import json
from pathlib import Path

from const import UPDATE_PLATFORMS

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "manifest.json"
HACS = ROOT / "hacs.json"


def test_datetime_platform_removed() -> None:
    assert "datetime" not in UPDATE_PLATFORMS


def test_manifest_version_present() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert "version" in manifest
    assert manifest["version"]


def test_manifest_and_hacs_min_homeassistant_version_match() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    hacs = json.loads(HACS.read_text(encoding="utf-8"))
    assert manifest["homeassistant"] == hacs["homeassistant"]
