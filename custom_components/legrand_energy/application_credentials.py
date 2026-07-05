"""Application credentials for Legrand Energy."""

from __future__ import annotations

from homeassistant.components.application_credentials import (
    ApplicationCredentials,
)

from .const import DOMAIN, AUTHORIZE_URL, TOKEN_URL


class LegrandApplicationCredentials(ApplicationCredentials):
    """OAuth application credentials."""

    domain = DOMAIN
    auth_implementation = "legrand_energy"

    def __init__(self) -> None:
        super().__init__()

    @property
    def authorize_url(self) -> str:
        """Authorize URL."""
        return AUTHORIZE_URL

    @property
    def token_url(self) -> str:
        """Token URL."""
        return TOKEN_URL
