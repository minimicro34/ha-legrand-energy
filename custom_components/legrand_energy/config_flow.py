"""Config flow for Legrand Energy."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN


class LegrandEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Legrand Energy."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        errors = {}

        if user_input is not None:
            await self.async_set_unique_id("legrand_energy")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="Legrand Energy",
                data={
                    "token": {
                        "access_token": user_input["access_token"],
                    }
                },
            )

        schema = vol.Schema(
            {
                vol.Required("access_token"): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )