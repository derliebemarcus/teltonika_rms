"""Unit tests for endpoint matrix loading."""

from __future__ import annotations

from pathlib import Path

from endpoint_matrix import load_endpoint_matrix


def test_load_endpoint_matrix_from_compiled_yaml(tmp_path: Path) -> None:
    compiled = tmp_path / "compiled.yaml"
    compiled.write_text(
        """
openapi: 3.0.1
paths:
  /v3/devices:
    get: {}
  /v3/devices/{id}:
    get: {}
  /v3/devices/status:
    get: {}
  /v3/devices/{id}/status:
    get: {}
  /v3/devices/{id}/location:
    get: {}
""",
        encoding="utf-8",
    )

    matrix = load_endpoint_matrix(str(compiled))
    assert matrix.path_for("devices_list") == "/v3/devices"
    assert matrix.path_for("device_detail") == "/v3/devices/{id}"
    assert matrix.path_for("device_state_aggregate") == "/v3/devices/status"
    assert matrix.path_for("device_state_single") == "/v3/devices/{id}/status"
    assert matrix.path_for("device_location") == "/v3/devices/{id}/location"


def test_load_endpoint_matrix_fallback_if_missing() -> None:
    matrix = load_endpoint_matrix("/tmp/does-not-exist.yaml")
    assert matrix.path_for("devices_list")
