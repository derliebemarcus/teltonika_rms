"""Diagnostics support for Teltonika RMS."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import TeltonikaRmsRuntime
from .const import AUTH_MODE_OAUTH2, CONF_AUTH_MODE

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
            "auth_mode": str(config_entry.data.get(CONF_AUTH_MODE, AUTH_MODE_OAUTH2)),
            "request_counter": runtime.bundle.api.request_counter,
            "inventory_devices": len(runtime.bundle.inventory.data),
            "state_devices": len(runtime.bundle.state.data),
            "aggregate_state_available": getattr(
                runtime.bundle.api, "_aggregate_state_available", None
            ),
            "monthly_request_estimate": getattr(
                runtime.bundle.state,
                "monthly_request_estimate",
                None,
            ),
            "endpoint_matrix_source": runtime.bundle.api.endpoint_matrix.source,
            "endpoint_matrix_paths": {
                key: spec.path for key, spec in runtime.bundle.api.endpoint_matrix.endpoints.items()
            },
        }
    return diagnostics
