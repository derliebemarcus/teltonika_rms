"""Diagnostics support for Teltonika RMS."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import TeltonikaRmsRuntime

TO_REDACT = {"access_token", "refresh_token", "token", "client_secret", "pat_token"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> dict[str, Any]:
    """Return redacted diagnostics for this config entry."""
    runtime: TeltonikaRmsRuntime | None = getattr(config_entry, "runtime_data", None)
    diagnostics: dict[str, Any] = {
        "entry": {
            "entry_id": config_entry.entry_id,
            "title": config_entry.title,
            "data": async_redact_data(dict(config_entry.data), TO_REDACT),
            "options": dict(config_entry.options),
        }
    }
    if runtime is not None:
        diagnostics["runtime"] = {
            "request_counter": runtime.bundle.api.request_counter,
            "inventory_devices": len(runtime.bundle.inventory.data),
            "state_devices": len(runtime.bundle.state.data),
            "endpoint_matrix_source": runtime.bundle.api.endpoint_matrix.source,
            "endpoint_matrix_paths": {
                key: spec.path for key, spec in runtime.bundle.api.endpoint_matrix.endpoints.items()
            },
        }
    return diagnostics
