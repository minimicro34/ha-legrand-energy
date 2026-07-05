"""OAuth2 implementation for Legrand Energy (Home Assistant native)."""

from __future__ import annotations

from homeassistant.components.application_credentials import (
    AbstractOAuth2Implementation,
)
from homeassistant.core import HomeAssistant

from .const import AUTHORIZE_URL, TOKEN_URL, SCOPES


class LegrandOAuth2Implementation(AbstractOAuth2Implementation):
    """OAuth2 implementation for Netatmo / Legrand."""

    def __init__(
        self,
        hass: HomeAssistant,
        client_id: str,
        client_secret: str,
    ) -> None:
        super().__init__(
            hass=hass,
            client_id=client_id,
            client_secret=client_secret,
        )

    @property
    def authorization_url(self) -> str:
        return AUTHORIZE_URL

    @property
    def token_url(self) -> str:
        return TOKEN_URL

    @property
    def scopes(self) -> list[str]:
        return SCOPES
