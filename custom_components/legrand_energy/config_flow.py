"""Config flow for Legrand Energy integration."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.components.application_credentials import AUTH_CALLBACK_PATH
from homeassistant.helpers.config_entry_oauth2_flow import (
    AbstractOAuth2FlowHandler,
)

from .const import DOMAIN


class LegrandEnergyConfigFlow(AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Handle OAuth2 config flow for Legrand Energy."""

    DOMAIN = DOMAIN

    @property
    def logger(self):
        """Return logger."""
        import logging
        return logging.getLogger(__name__)

    async def async_oauth_create_entry(self, data):
        """Create config entry after successful OAuth."""
        return self.async_create_entry(
            title="Legrand Energy",
            data=data,
        )
