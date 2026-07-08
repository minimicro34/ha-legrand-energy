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

        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id("legrand_energy")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="Legrand Energy",
                data={
                    "client_id": user_input["client_id"],
                    "client_secret": user_input["client_secret"],
                    "access_token": user_input["access_token"],
                    "refresh_token": user_input["refresh_token"],
                    "web_token": user_input["web_token"],
                },
            )

        schema = vol.Schema(
            {
                vol.Required("client_id"): str,
                vol.Required("client_secret"): str,
                vol.Required("access_token"): str,
                vol.Required("refresh_token"): str,
                vol.Optional(
                    "web_token",
                    default=user_input.get("web_token", "") if user_input else "",
                ): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
    @staticmethod
    def async_get_options_flow(config_entry):
        """Return options flow."""
        from .options_flow import LegrandEnergyOptionsFlow

        return LegrandEnergyOptionsFlow(config_entry)