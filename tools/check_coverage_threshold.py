#!/usr/bin/env python3
"""Fail when coverage.xml is below the required percentage threshold."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: check_coverage_threshold.py <coverage.xml> <minimum_percent>")
        return 2

    coverage_path = Path(sys.argv[1])
    minimum = float(sys.argv[2])

    if not coverage_path.exists():
        print(f"Coverage file not found: {coverage_path}")
        return 2

    root = ET.fromstring(coverage_path.read_text(encoding="utf-8"))
    line_rate_raw = root.attrib.get("line-rate")
    if line_rate_raw is None:
        print(f"Coverage file does not contain a line-rate: {coverage_path}")
        return 2

    actual = float(line_rate_raw) * 100
    if actual < minimum:
        print(f"Coverage check failed: {actual:.2f}% is below required {minimum:.2f}%.")
        return 1

    print(f"Coverage check passed: {actual:.2f}% >= {minimum:.2f}%.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
