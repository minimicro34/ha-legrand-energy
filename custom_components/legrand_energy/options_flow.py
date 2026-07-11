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
                        default=self._config_entry.options.get(
                            "web_token",
                            self._config_entry.data.get("web_token", ""),
                        ),
                    ): str,
                }
            ),
        )
