"""Datetime entities for Teltonika RMS."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TeltonikaRmsRuntime
from .coordinator import CoordinatorBundle
from .entity import TeltonikaRmsEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: TeltonikaRmsRuntime = entry.runtime_data
    bundle: CoordinatorBundle = runtime.bundle
    known: set[str] = set()

    @callback
    def _add_new_entities() -> None:
        new_entities: list[RmsLastSeenDateTime] = []
        for device_id in bundle.inventory.data:
            unique = f"{device_id}_last_seen"
            if unique in known:
                continue
            known.add(unique)
            new_entities.append(RmsLastSeenDateTime(bundle, device_id))
        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(bundle.inventory.async_add_listener(_add_new_entities))


class RmsLastSeenDateTime(TeltonikaRmsEntity, DateTimeEntity):
    """Last update timestamp from RMS."""

    _attr_translation_key = "last_seen"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, bundle: CoordinatorBundle, device_id: str) -> None:
        super().__init__(bundle, device_id)
        self._attr_unique_id = f"{device_id}_last_seen"

    @property
    def native_value(self) -> datetime | None:
        normalized = self._normalized
        return normalized.last_seen if normalized else None
