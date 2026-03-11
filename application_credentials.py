"""Application credentials support for Teltonika RMS OAuth2."""

from __future__ import annotations

from homeassistant.components.application_credentials import (
    AuthorizationServer,
    ClientCredential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import (
    AbstractOAuth2Implementation,
    LocalOAuth2ImplementationWithPkce,
)

from .const import AUTHORIZE_URL, TOKEN_URL


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return OAuth2 authorization server metadata."""
    return AuthorizationServer(
        authorize_url=AUTHORIZE_URL,
        token_url=TOKEN_URL,
    )


async def async_get_auth_implementation(
    hass: HomeAssistant,
    auth_domain: str,
    credential: ClientCredential,
) -> AbstractOAuth2Implementation:
    """Build a PKCE OAuth2 implementation."""
    return LocalOAuth2ImplementationWithPkce(
        hass,
        auth_domain,
        credential.client_id,
        credential.client_secret,
        AUTHORIZE_URL,
        TOKEN_URL,
    )


async def async_get_description_placeholders(hass: HomeAssistant) -> dict[str, str]:
    """Add dynamic placeholders for credentials form."""
    return {
        "console_url": "https://rms.teltonika-networks.com/",
    }
