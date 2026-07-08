"""Options flow for Legrand Energy."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries


class LegrandEnergyOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Legrand Energy."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    "web_token": user_input.get("web_token", ""),
                },
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "web_token",
                        default=self.config_entry.options.get("web_token", ""),
                    ): str,
                }
            ),
        )