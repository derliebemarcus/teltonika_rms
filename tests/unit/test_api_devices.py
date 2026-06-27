"""Tests for current RMS device-list schema and pagination behavior."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.teltonika_rms.api import RmsAuthClient
from custom_components.teltonika_rms.api_devices import (
    SpecCompatibleRmsApiClient,
    _has_next_offset_page,
)
from custom_components.teltonika_rms.endpoint_matrix import EndpointMatrix, EndpointSpec


def _client() -> SpecCompatibleRmsApiClient:
    matrix = EndpointMatrix(
        source="test",
        endpoints={"devices_list": EndpointSpec("/devices", tuple(), "safe")},
    )
    return SpecCompatibleRmsApiClient(
        cast(RmsAuthClient, MagicMock()),
        matrix,
    )


@pytest.mark.asyncio
async def test_device_list_uses_limit_offset_and_meta_total(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The current RMS specification uses offset pagination and meta.total."""
    client = _client()
    request = AsyncMock(
        side_effect=[
            ([{"id": 1, "status": 1}], {"total": 2}),
            ([{"id": 2, "status": 0}], {"total": 2}),
        ]
    )
    monkeypatch.setattr(client, "async_request", request)

    devices = await client.async_list_devices(page_size=1, max_pages=5)

    assert devices == [{"id": 1, "status": 1}, {"id": 2, "status": 0}]
    assert request.await_count == 2
    assert request.await_args_list[0].kwargs["params"] == {"limit": 1, "offset": 0}
    assert request.await_args_list[1].kwargs["params"] == {"limit": 1, "offset": 1}


@pytest.mark.asyncio
async def test_device_list_preserves_existing_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Existing status and tag options remain attached to the corrected request."""
    client = _client()
    request = AsyncMock(return_value=([{"id": 1, "status": 1}], {"total": 1}))
    monkeypatch.setattr(client, "async_request", request)

    await client.async_list_devices(tags=["ber", "zrh"], device_status="online")

    assert request.await_args.kwargs["params"] == {
        "limit": 50,
        "offset": 0,
        "tags": "ber,zrh",
        "status": "online",
    }


def test_offset_page_fallback_uses_short_page_detection() -> None:
    """Without meta.total, a short page terminates pagination safely."""
    full_batch: list[dict[str, Any]] = [{"id": index} for index in range(2)]
    assert _has_next_offset_page(full_batch, {}, 0, 2) is True
    assert _has_next_offset_page([{"id": 1}], {}, 0, 2) is False
    assert _has_next_offset_page([], {"total": 10}, 0, 2) is False
