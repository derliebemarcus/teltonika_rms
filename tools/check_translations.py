#!/usr/bin/env python3
"""Validate translation files against the German reference strings."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ROOT / "strings.json"
TRANSLATIONS_DIR = ROOT / "translations"

PLACEHOLDER_PATTERNS = (
    re.compile(r"__[^_]+__"),
    re.compile(r"\[\[\d+\]\]"),
    re.compile(r"\[\[[^\]]*$"),
)


def _flatten(node: Any, prefix: str = "") -> dict[str, str]:
    output: dict[str, str] = {}
    if isinstance(node, dict):
        for key, value in node.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            output.update(_flatten(value, child_prefix))
    elif isinstance(node, str):
        output[prefix] = node
    return output


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    reference_data = _load_json(REFERENCE)
    reference_keys = set(_flatten(reference_data))

    errors: list[str] = []
    for file_path in sorted(TRANSLATIONS_DIR.glob("*.json")):
        data = _load_json(file_path)
        flattened = _flatten(data)
        keys = set(flattened)

        missing = sorted(reference_keys - keys)
        extra = sorted(keys - reference_keys)
        if missing:
            errors.append(
                f"{file_path.name}: missing keys: {missing[:5]}{'...' if len(missing) > 5 else ''}"
            )
        if extra:
            errors.append(
                f"{file_path.name}: extra keys: {extra[:5]}{'...' if len(extra) > 5 else ''}"
            )

        for key, text in flattened.items():
            for pattern in PLACEHOLDER_PATTERNS:
                if pattern.search(text):
                    errors.append(
                        f"{file_path.name}:{key}: unresolved placeholder pattern in '{text}'"
                    )
                    break

    if errors:
        print("Translation validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("All translation files are consistent with strings.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
