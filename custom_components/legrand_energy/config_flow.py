"""Config flow for Legrand Energy."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlowResult
from homeassistant.helpers import config_entry_oauth2_flow, selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .authentication_store import PRIVATE_COOKIE_NAMES
from .const import DOMAIN, OAUTH_SCOPES
from .services.private import (
    PrivateAuthService,
    PrivateAuthServiceAuthenticationError,
    PrivateAuthServiceError,
)

_LOGGER = logging.getLogger(__name__)

PRIVATE_AUTH_KEYS = (
    "web_token",
    *PRIVATE_COOKIE_NAMES,
)


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

        if self.source == SOURCE_REAUTH:
            self._abort_if_unique_id_mismatch()
        else:
            self._abort_if_unique_id_configured()

        return await self.async_step_pick_implementation(user_input)

    async def async_oauth_create_entry(
        self,
        data: dict[str, Any],
    ) -> ConfigFlowResult:
        """Create or update the OAuth configuration."""
        if self.source == SOURCE_REAUTH:
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(),
                data_updates=data,
            )

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

            try:
                private_service = PrivateAuthService(
                    session=async_get_clientsession(self.hass),
                )

                private_session = await private_service.login(
                    username=username,
                    password=password,
                )

            except PrivateAuthServiceAuthenticationError:
                errors["base"] = "invalid_auth"

            except (
                PrivateAuthServiceError,
                aiohttp.ClientError,
                TimeoutError,
            ):
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
                    title="Legrand EcoMeter",
                    data=entry_data,
                )

        return self.async_show_form(
            step_id="private",
            data_schema=vol.Schema(
                {
                    vol.Required("username"): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.EMAIL,
                        )
                    ),
                    vol.Required("password"): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Reconfigure private Home + Control credentials."""
        entry = self._get_reconfigure_entry()
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

            except (
                PrivateAuthServiceError,
                aiohttp.ClientError,
                TimeoutError,
            ):
                errors["base"] = "cannot_connect"

            else:
                new_data: dict[str, Any] = dict(entry.data)

                new_data["username"] = username
                new_data["password"] = password

                # Remove the complete previous private authentication
                # session before storing the newly authenticated one.
                for key in PRIVATE_AUTH_KEYS:
                    new_data.pop(key, None)

                new_data["web_token"] = private_session.web_token

                for config_key, cookie_name in PRIVATE_COOKIE_NAMES.items():
                    cookie_value = private_session.cookies.get(cookie_name)

                    if cookie_value:
                        new_data[config_key] = cookie_value

                return self.async_update_reload_and_abort(
                    entry,
                    data=new_data,
                )

        username = entry.data.get("username")
        username_default = username if isinstance(username, str) else ""

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "username",
                        default=username_default,
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.EMAIL,
                        )
                    ),
                    vol.Required("password"): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: Mapping[str, Any],
    ) -> ConfigFlowResult:
        """Start OAuth reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Confirm OAuth reauthentication."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=vol.Schema({}),
            )

        return await self.async_step_user()
