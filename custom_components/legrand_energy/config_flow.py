"""Config flow for Legrand Energy."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN


class LegrandEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Simple config flow (safe version)."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="Legrand Energy",
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required("subscription_key"): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
        )
