"""Options flow for Legrand Energy."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .authentication_store import PRIVATE_COOKIE_NAMES
from .services.private import (
    PrivateAuthService,
    PrivateAuthServiceAuthenticationError,
    PrivateAuthServiceError,
)

PRIVATE_AUTH_KEYS = (
    "web_token",
    *PRIVATE_COOKIE_NAMES,
)


class LegrandEnergyOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Legrand Energy."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    def _current_value(self, key: str) -> str:
        """Return the current persisted value."""
        value = self._config_entry.data.get(key)

        return value if isinstance(value, str) else ""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage private Netatmo credentials."""
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
                new_data = dict(self._config_entry.data)

                new_data["username"] = user_input["username"]
                new_data["password"] = user_input["password"]

                for key in PRIVATE_AUTH_KEYS:
                    new_data.pop(key, None)

                new_data["web_token"] = private_session.web_token

                for config_key, cookie_name in PRIVATE_COOKIE_NAMES.items():
                    cookie_value = private_session.cookies.get(cookie_name)

                    if cookie_value:
                        new_data[config_key] = cookie_value

                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data=new_data,
                    options={},
                )

                return self.async_create_entry(
                    title="",
                    data={},
                )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "username",
                        default=self._current_value("username"),
                    ): str,
                    vol.Required("password"): str,
                }
            ),
            errors=errors,
        )