#!/usr/bin/env python3
"""Generate frozen RMS endpoint matrix JSON from compiled OpenAPI YAML."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


def _extract_scopes(operation: dict, default_security: list) -> list[str]:
    scopes: list[str] = []
    security = operation.get("security", default_security)
    if not isinstance(security, list):
        return scopes
    for item in security:
        if not isinstance(item, dict):
            continue
        for raw_scopes in item.values():
            if not isinstance(raw_scopes, list):
                continue
            for scope in raw_scopes:
                if isinstance(scope, str) and scope not in scopes:
                    scopes.append(scope)
    return scopes


def _polling_hint(path: str) -> str:
    lower = path.lower()
    if "location" in lower:
        return "high-cost"
    if "status" in lower:
        return "async-channel"
    return "safe"


def _pick_best(candidates: list[tuple[str, list[str]]]) -> tuple[str, list[str]] | None:
    if not candidates:
        return None
    candidates.sort(key=lambda item: (0 if item[0].startswith("/v3/") else 1, len(item[0])))
    return candidates[0]


def _is_aggregate_status_candidate(path: str) -> bool:
    lower = path.lower()
    if "{" in lower:
        return False
    if "devices" not in lower:
        return False
    return lower.endswith("/status") and "/connect/" not in lower


def build_matrix(compiled_spec: dict) -> dict:
    paths = compiled_spec.get("paths", {})
    default_security = compiled_spec.get("security", [])
    buckets: dict[str, list[tuple[str, list[str]]]] = {
        "devices_list": [],
        "device_detail": [],
        "device_state_aggregate": [],
        "device_state_single": [],
        "device_location": [],
    }

    for path, methods in paths.items():
        if not isinstance(path, str) or not isinstance(methods, dict):
            continue
        operation = methods.get("get")
        if not isinstance(operation, dict):
            continue
        lower = path.lower()
        if "devices" not in lower:
            continue
        scopes = _extract_scopes(operation, default_security)
        if lower.endswith("/devices") or lower.endswith("/devices/"):
            buckets["devices_list"].append((path, scopes))
        elif "/devices/" in lower and lower.endswith("/status"):
            buckets["device_state_single"].append((path, scopes))
        elif "/devices/" in lower and lower.endswith("/location"):
            buckets["device_location"].append((path, scopes))
        elif _is_aggregate_status_candidate(path):
            buckets["device_state_aggregate"].append((path, scopes))
        elif "/devices/" in lower and "{" in path:
            buckets["device_detail"].append((path, scopes))

    defaults = {
        "devices_list": ("/v3/devices", ["devices:read"]),
        "device_detail": ("/v3/devices/{id}", ["devices:read"]),
        "device_state_aggregate": ("/v3/devices/status", ["devices:read"]),
        "device_state_single": ("/v3/devices/{id}/status", ["devices:read"]),
        "device_location": ("/v3/devices/{id}/location", ["device_location:read"]),
    }

    endpoints: dict[str, dict] = {}
    for key, default_value in defaults.items():
        selected = _pick_best(buckets[key]) or default_value
        endpoints[key] = {
            "path": selected[0],
            "scopes": selected[1],
            "polling": _polling_hint(selected[0]),
        }

    return {
        "version": 1,
        "generated_from": "compiled.yaml",
        "endpoints": endpoints,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: generate_rms_endpoint_matrix.py <compiled.yaml> [output.json]")
        return 1

    input_path = Path(sys.argv[1]).expanduser()
    default_output = Path(__file__).resolve().parent.parent / "endpoint_matrix_frozen.json"
    output_path = Path(sys.argv[2]).expanduser() if len(sys.argv) > 2 else default_output

    compiled_spec = yaml.safe_load(input_path.read_text(encoding="utf-8"))
    matrix = build_matrix(compiled_spec)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote endpoint matrix to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
