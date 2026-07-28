"""Config flow for Legrand Energy."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .authentication_store import PRIVATE_COOKIE_NAMES
from .const import DOMAIN
from .options_flow import LegrandEnergyOptionsFlow
from .services.private import (
    PrivateAuthService,
    PrivateAuthServiceAuthenticationError,
    PrivateAuthServiceError,
)


class LegrandEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Legrand Energy."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            private_service = PrivateAuthService(session=session)

            try:
                private_session = await private_service.login(
                    username=user_input["username"],
                    password=user_input["password"],
                )

            except PrivateAuthServiceAuthenticationError:
                errors["base"] = "invalid_auth"

            except PrivateAuthServiceError:
                errors["base"] = "cannot_connect"

            else:
                await self.async_set_unique_id("legrand_energy")
                self._abort_if_unique_id_configured()

                entry_data: dict[str, Any] = {
                    "client_id": user_input["client_id"],
                    "client_secret": user_input["client_secret"],
                    "access_token": user_input["access_token"],
                    "refresh_token": user_input["refresh_token"],
                    "username": user_input["username"],
                    "password": user_input["password"],
                    "web_token": private_session.web_token,
                }

                for config_key, cookie_name in PRIVATE_COOKIE_NAMES.items():
                    cookie_value = private_session.cookies.get(cookie_name)

                    if cookie_value:
                        entry_data[config_key] = cookie_value

                return self.async_create_entry(
                    title="Legrand Energy",
                    data=entry_data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("client_id"): str,
                    vol.Required("client_secret"): str,
                    vol.Required("access_token"): str,
                    vol.Required("refresh_token"): str,
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return LegrandEnergyOptionsFlow(config_entry)