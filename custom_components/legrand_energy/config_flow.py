"""Config flow for Legrand Energy."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult

from .const import DOMAIN
from .options_flow import LegrandEnergyOptionsFlow


class LegrandEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Legrand Energy."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step."""
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
                    "web_token": user_input.get("web_token", ""),
                    "refresh_token_web": user_input.get(
                        "refresh_token_web",
                        "",
                    ),
                    "laravel_session": user_input.get(
                        "laravel_session",
                        "",
                    ),
                    "mail_cookie": user_input.get("mail_cookie", ""),
                    "authorize_state": user_input.get(
                        "authorize_state",
                        "",
                    ),
                    "xsrf_token": user_input.get("xsrf_token", ""),
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("client_id"): str,
                    vol.Required("client_secret"): str,
                    vol.Required("access_token"): str,
                    vol.Required("refresh_token"): str,
                    vol.Optional("web_token", default=""): str,
                    vol.Optional("refresh_token_web", default=""): str,
                    vol.Optional("laravel_session", default=""): str,
                    vol.Optional("mail_cookie", default=""): str,
                    vol.Optional("authorize_state", default=""): str,
                    vol.Optional("xsrf_token", default=""): str,
                }
            ),
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return LegrandEnergyOptionsFlow(config_entry)
