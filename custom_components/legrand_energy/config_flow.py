"""Config flow for Legrand Energy integration."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN


class LegrandEnergyConfigFlow(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler,
    domain=DOMAIN,
):
    """Handle OAuth2 config flow."""

    DOMAIN = DOMAIN

    async def async_oauth_create_entry(self, data):
        """Create entry after OAuth login."""
        return self.async_create_entry(
            title="Legrand Energy",
            data=data,
        )
