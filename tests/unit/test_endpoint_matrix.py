"""Unit tests for endpoint matrix loading."""

from __future__ import annotations

from pathlib import Path

from endpoint_matrix import (
    EndpointMatrix,
    EndpointSpec,
    _extract_scopes,
    _is_aggregate_status_candidate,
    _pick_best,
    _polling_hint,
    load_endpoint_matrix,
)


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


def test_load_endpoint_matrix_handles_invalid_yaml_and_shape(tmp_path: Path) -> None:
    broken = tmp_path / "broken.yaml"
    broken.write_text("paths: [broken", encoding="utf-8")
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("- nope", encoding="utf-8")

    broken_matrix = load_endpoint_matrix(str(broken))
    invalid_matrix = load_endpoint_matrix(str(invalid))

    assert broken_matrix.path_for("devices_list")
    assert invalid_matrix.path_for("devices_list")


def test_endpoint_matrix_helpers_cover_selection_and_scopes() -> None:
    spec = EndpointSpec(path="/v3/devices/{id}", scopes=("devices:read",), polling="safe")
    matrix = EndpointMatrix(source="x", endpoints={"device": spec})

    assert matrix.path_for("device") == "/v3/devices/{id}"
    assert matrix.path_for("missing") is None
    assert matrix.scopes_for("device") == ("devices:read",)
    assert matrix.scopes_for("missing") == ()
    assert matrix.format_path("device", id="abc") == "/v3/devices/abc"
    assert matrix.format_path("missing", id="abc") is None

    operation = {
        "security": [
            {"oauth": ["devices:read", "devices:read"]},
            {"other": ["device_location:read"]},
        ]
    }
    assert _extract_scopes(operation, []) == ("devices:read", "device_location:read")
    assert _extract_scopes({"security": "broken"}, []) == ()

    assert _polling_hint("/v3/devices/status") == "async-channel"
    assert _polling_hint("/v3/devices/{id}/location") == "high-cost"
    assert _polling_hint("/v3/devices") == "safe"

    best = _pick_best(
        [
            EndpointSpec(path="/v2/devices/status/verbose", scopes=(), polling="async-channel"),
            EndpointSpec(path="/v3/devices/status", scopes=(), polling="async-channel"),
        ]
    )
    assert best is not None
    assert best.path == "/v3/devices/status"
    assert _pick_best([]) is None

    assert _is_aggregate_status_candidate("/v3/devices/status") is True
    assert _is_aggregate_status_candidate("/v3/devices/{id}/status") is False
    assert _is_aggregate_status_candidate("/v3/devices/connect/status") is False
    assert _is_aggregate_status_candidate("/v3/users/status") is False
