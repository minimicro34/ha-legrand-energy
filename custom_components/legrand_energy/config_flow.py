"""Config flow for Legrand Energy."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .authentication_store import PRIVATE_COOKIE_NAMES
from .const import DOMAIN, OAUTH_SCOPES
from .options_flow import LegrandEnergyOptionsFlow
from .services.private import (
    PrivateAuthService,
    PrivateAuthServiceAuthenticationError,
    PrivateAuthServiceError,
)

_LOGGER = logging.getLogger(__name__)


class LegrandEnergyConfigFlow(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler,
    domain=DOMAIN,
):
    """Handle a config flow for Legrand Energy."""

    DOMAIN = DOMAIN
    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self._oauth_data: dict[str, Any] | None = None

    @property
    def logger(self) -> logging.Logger:
        """Return the logger."""
        return _LOGGER

    @property
    def extra_authorize_data(self) -> dict[str, str]:
        """Return additional OAuth authorization parameters."""
        return {
            "scope": " ".join(OAUTH_SCOPES),
        }

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Start the OAuth flow."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        return await self.async_step_pick_implementation(user_input)

    async def async_oauth_create_entry(
        self,
        data: dict[str, Any],
    ) -> ConfigFlowResult:
        """Store OAuth data and continue with private authentication."""
        self._oauth_data = data
        return await self.async_step_private()

    async def async_step_private(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Authenticate against the private Netatmo web service."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input["username"]
            password = user_input["password"]

            private_service = PrivateAuthService(
                session=async_get_clientsession(self.hass),
            )

            try:
                private_session = await private_service.login(
                    username=username,
                    password=password,
                )

            except PrivateAuthServiceAuthenticationError:
                errors["base"] = "invalid_auth"

            except (PrivateAuthServiceError, aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"

            else:
                if self._oauth_data is None:
                    return self.async_abort(reason="oauth_error")

                entry_data: dict[str, Any] = {
                    **self._oauth_data,
                    "username": username,
                    "password": password,
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
            step_id="private",
            data_schema=vol.Schema(
                {
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
