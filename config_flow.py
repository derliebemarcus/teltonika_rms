"""Config flow for Teltonika RMS."""

from __future__ import annotations

import base64
import json
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_entry_oauth2_flow

from .api import estimate_monthly_requests, normalize_tags
from .const import (
    CONF_DEVICE_STATUS,
    CONF_ENABLE_LOCATION,
    CONF_ESTIMATED_DEVICES,
    CONF_INVENTORY_INTERVAL,
    CONF_SPEC_PATH,
    CONF_STATE_INTERVAL,
    CONF_TAGS,
    DEFAULT_OPTIONS,
    DEFAULT_SPEC_PATH,
    DOMAIN,
    MAX_MONTHLY_REQUESTS,
    OAUTH2_SCOPES,
    REQUEST_BUDGET_HEADROOM,
)
from .endpoint_matrix import load_endpoint_matrix


class OAuth2FlowHandler(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Handle OAuth2 config flow for Teltonika RMS."""

    DOMAIN = DOMAIN
    VERSION = 1

    _reauth_entry: ConfigEntry | None = None

    @property
    def extra_authorize_data(self) -> dict[str, str]:
        """Append OAuth scopes during authorize step."""
        return {"scope": " ".join(OAUTH2_SCOPES)}

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Begin reauthentication."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await super().async_step_reauth(entry_data)

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> FlowResult:
        """Create (or update) entry once OAuth callback is complete."""
        unique_id = _extract_subject_from_token(data)
        if unique_id:
            await self.async_set_unique_id(unique_id)
            if self.source != "reauth":
                self._abort_if_unique_id_configured()

        if self.source == "reauth":
            if self._reauth_entry is not None:
                if unique_id and self._reauth_entry.unique_id and self._reauth_entry.unique_id != unique_id:
                    return self.async_abort(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data_updates=data,
                )

        return self.async_create_entry(
            title="Teltonika RMS",
            data=data,
            options=dict(DEFAULT_OPTIONS),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return options flow handler."""
        return TeltonikaRmsOptionsFlow(config_entry)


class TeltonikaRmsOptionsFlow(OptionsFlow):
    """Options flow with request-budget safety checks."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            normalized = dict(user_input)
            normalized[CONF_TAGS] = ",".join(normalize_tags(str(user_input.get(CONF_TAGS, ""))))

            inventory_interval = int(normalized[CONF_INVENTORY_INTERVAL])
            state_interval = int(normalized[CONF_STATE_INTERVAL])
            estimated_devices = int(normalized[CONF_ESTIMATED_DEVICES])
            spec_path = str(normalized[CONF_SPEC_PATH]).strip() or DEFAULT_SPEC_PATH

            matrix = await self.hass.async_add_executor_job(load_endpoint_matrix, spec_path)
            aggregate_supported = matrix.path_for("device_state_aggregate") is not None

            estimate = estimate_monthly_requests(
                inventory_interval=inventory_interval,
                state_interval=state_interval,
                estimated_devices=estimated_devices,
                aggregate_state_supported=aggregate_supported,
            )
            if estimate > int(MAX_MONTHLY_REQUESTS * REQUEST_BUDGET_HEADROOM):
                errors["base"] = "request_budget_exceeded"
            else:
                normalized[CONF_SPEC_PATH] = spec_path
                return self.async_create_entry(title="", data=normalized)

        merged = dict(DEFAULT_OPTIONS)
        merged.update(self._config_entry.options)
        schema = vol.Schema(
            {
                vol.Required(CONF_INVENTORY_INTERVAL, default=merged[CONF_INVENTORY_INTERVAL]): vol.All(
                    vol.Coerce(int), vol.Range(min=60, max=3600)
                ),
                vol.Required(CONF_STATE_INTERVAL, default=merged[CONF_STATE_INTERVAL]): vol.All(
                    vol.Coerce(int), vol.Range(min=60, max=3600)
                ),
                vol.Required(CONF_ESTIMATED_DEVICES, default=merged[CONF_ESTIMATED_DEVICES]): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=500)
                ),
                vol.Required(CONF_TAGS, default=merged[CONF_TAGS]): str,
                vol.Required(CONF_DEVICE_STATUS, default=merged[CONF_DEVICE_STATUS]): str,
                vol.Required(CONF_SPEC_PATH, default=merged[CONF_SPEC_PATH]): str,
                vol.Required(CONF_ENABLE_LOCATION, default=merged[CONF_ENABLE_LOCATION]): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)


def _extract_subject_from_token(data: dict[str, Any]) -> str | None:
    token = data.get("token", {})
    if not isinstance(token, dict):
        return None
    raw_access_token = token.get(CONF_ACCESS_TOKEN)
    if not isinstance(raw_access_token, str):
        return None
    parts = raw_access_token.split(".")
    if len(parts) < 2:
        return None
    payload_segment = parts[1]
    padded = payload_segment + "=" * (-len(payload_segment) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
        payload = json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return None
    subject = payload.get("sub")
    return str(subject) if subject is not None else None
