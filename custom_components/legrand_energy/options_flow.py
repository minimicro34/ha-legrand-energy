"""Options flow for Legrand Energy."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult


class LegrandEnergyOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Legrand Energy."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    def _current_value(self, key: str) -> str:
        """Return the current persisted value."""
        data_value = self._config_entry.data.get(key)

        if isinstance(data_value, str) and data_value:
            return data_value

        option_value = self._config_entry.options.get(key)

        return option_value if isinstance(option_value, str) else ""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._config_entry.title,
                data=user_input,
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "web_token",
                        default=self._current_value("web_token"),
                    ): str,
                    vol.Optional(
                        "refresh_token_web",
                        default=self._current_value("refresh_token_web"),
                    ): str,
                    vol.Optional(
                        "laravel_session",
                        default=self._current_value("laravel_session"),
                    ): str,
                    vol.Optional(
                        "mail_cookie",
                        default=self._current_value("mail_cookie"),
                    ): str,
                    vol.Optional(
                        "authorize_state",
                        default=self._current_value("authorize_state"),
                    ): str,
                    vol.Optional(
                        "xsrf_token",
                        default=self._current_value("xsrf_token"),
                    ): str,
                }
            ),
        )
