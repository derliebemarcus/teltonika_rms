"""Contract fixtures derived from representative RMS schema examples."""

from __future__ import annotations

import json
from pathlib import Path

from teltonika_rms.api import _coerce_list, _parse_envelope
from teltonika_rms.models import normalize_device

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "rms"


def test_device_full_fixture_normalizes_expected_runtime_fields() -> None:
    payload = json.loads((FIXTURES / "device_full.json").read_text(encoding="utf-8"))
    normalized = normalize_device(payload)

    assert normalized is not None
    assert normalized.firmware == "RUT9XX_R_00.06.05.3"
    assert normalized.clients_count == 3
    assert normalized.router_uptime == 3060
    assert normalized.temperature == 360
    assert normalized.signal_strength == -81
    assert normalized.connection_type == "LTE"


def test_firmware_files_fixture_parses_rms_envelope() -> None:
    payload = json.loads((FIXTURES / "files_firmware.json").read_text(encoding="utf-8"))
    data, meta = _parse_envelope(payload)

    assert meta == {"total": 1}
    assert _coerce_list(data) == data
    assert data[0]["type"] == "firmware"
