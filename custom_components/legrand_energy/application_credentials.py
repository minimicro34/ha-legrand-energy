"""Application credentials support for Legrand Energy."""

from __future__ import annotations

from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant

from .const import OAUTH_AUTHORIZE_URL, OAUTH_TOKEN_URL


async def async_get_authorization_server(
    hass: HomeAssistant,
) -> AuthorizationServer:
    """Return the Netatmo authorization server."""
    return AuthorizationServer(
        authorize_url=OAUTH_AUTHORIZE_URL,
        token_url=OAUTH_TOKEN_URL,
    )


async def async_get_description_placeholders(
    hass: HomeAssistant,
) -> dict[str, str]:
    """Return placeholders for the application credentials dialog."""
    return {
        "console_url": "https://dev.netatmo.com/apps/",
    }
