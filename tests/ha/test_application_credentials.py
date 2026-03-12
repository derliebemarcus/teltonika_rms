"""Tests for OAuth application credential wiring."""

from __future__ import annotations

import asyncio

import pytest

from homeassistant.components.application_credentials import ClientCredential
from homeassistant.helpers.config_entry_oauth2_flow import (
    LocalOAuth2ImplementationWithPkce,
)

from teltonika_rms.application_credentials import async_get_auth_implementation
from teltonika_rms.const import AUTHORIZE_URL, TOKEN_URL

pytestmark = pytest.mark.ha


def test_async_get_auth_implementation_uses_correct_pkce_argument_order() -> None:
    implementation = asyncio.run(
        async_get_auth_implementation(
            hass=object(),  # type: ignore[arg-type]
            auth_domain="teltonika_rms.test",
            credential=ClientCredential(
                client_id="client-id",
                client_secret="client-secret",
            ),
        )
    )

    assert isinstance(implementation, LocalOAuth2ImplementationWithPkce)
    assert implementation.domain == "teltonika_rms.test"
    assert implementation.client_id == "client-id"
    assert implementation.client_secret == "client-secret"
    assert implementation.authorize_url == AUTHORIZE_URL
    assert implementation.token_url == TOKEN_URL
