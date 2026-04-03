"""Shared pytest configuration for Teltonika RMS tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Find the true project root by looking for custom_components
current = Path(__file__).resolve()
TEST_ROOT = current.parents[1]

# Prioritize the directory where the tests are running (e.g. mutants/)

if str(TEST_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT.parent))
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

# Find the true project root for resources that might not be copied by mutmut
REAL_ROOT = TEST_ROOT
for parent in current.parents:
    if (parent / "custom_components" / "teltonika_rms" / "manifest.json").exists():
        REAL_ROOT = parent
        break


# Add real root as fallback in case tests are importing something unmutated
if str(REAL_ROOT.parent) not in sys.path:
    sys.path.append(str(REAL_ROOT.parent))
if str(REAL_ROOT) not in sys.path:
    sys.path.append(str(REAL_ROOT))
pytest_plugins = ("pytest_asyncio",)
