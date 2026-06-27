"""OpenAPI-compatible device inventory client behavior."""

from __future__ import annotations

from typing import Any

from .api import RmsApiClient, _coerce_list, _validate_contract_list
from .exceptions import RmsApiError
from .models_api import DeviceListResponse


class SpecCompatibleRmsApiClient(RmsApiClient):
    """RMS API client with device-list pagination matching the current OpenAPI spec."""

    async def async_list_devices(
        self,
        *,
        tags: list[str] | None = None,
        device_status: str | None = None,
        page_size: int = 50,
        max_pages: int = 20,
    ) -> list[dict[str, Any]]:
        """Fetch devices using the documented limit/offset pagination contract."""
        path = self.endpoint_matrix.path_for("devices_list")
        if not path:
            raise RmsApiError("No devices list endpoint configured")

        offset = 0
        devices: list[dict[str, Any]] = []

        for _page in range(max_pages):
            params: dict[str, Any] = {"limit": page_size, "offset": offset}
            if tags:
                # Preserve the integration's existing tag-filter behavior until the
                # options flow is migrated from tag names to documented tag IDs.
                params["tags"] = ",".join(tags)
            if device_status:
                params["status"] = device_status

            data, meta = await self.async_request("GET", path, params=params)
            batch = _coerce_list(data)
            _validate_contract_list(batch, "devices_list", DeviceListResponse)
            devices.extend(batch)

            if not _has_next_offset_page(batch, meta, offset):
                break
            offset += page_size

        return devices


def _has_next_offset_page(
    batch: list[dict[str, Any]],
    meta: dict[str, Any],
    offset: int,
) -> bool:
    """Return whether another offset page exists according to RMS metadata."""
    total = meta.get("total")
    if isinstance(total, int):
        return bool(batch) and offset + len(batch) < total
    return bool(batch)
