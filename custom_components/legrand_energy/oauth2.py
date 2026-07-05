"""OAuth2 implementation for Legrand Energy (Home Assistant native)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.application_credentials import (
    AuthImplementation,
)
from homeassistant.core import HomeAssistant

from .const import (
    AUTHORIZE_URL,
    TOKEN_URL,
    SCOPES,
)


class LegrandOAuth2Implementation(AuthImplementation):
    """OAuth2 implementation for Netatmo / Legrand Home + Control."""

    def __init__(
        self,
        hass: HomeAssistant,
        client_id: str,
        client_secret: str,
    ) -> None:
        super().__init__(
            hass=hass,
            auth_implementation_name="legrand_energy",
            client_id=client_id,
            client_secret=client_secret,
        )

    @property
    def authorization_url(self) -> str:
        """Return authorization URL."""
        return AUTHORIZE_URL

    @property
    def token_url(self) -> str:
        """Return token URL."""
        return TOKEN_URL

    @property
    def scopes(self) -> list[str]:
        """OAuth scopes required."""
        return SCOPES

    async def async_refresh_token(self, token: dict[str, Any]) -> dict[str, Any]:
        """Refresh token (handled by HA base class)."""
        return await super().async_refresh_token(token)
