"""Config flow for Legrand Energy integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_SUBSCRIPTION_KEY,
)


class LegrandEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Legrand Energy."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """First step: collect API credentials."""

        errors = {}

        if user_input is not None:
            return self.async_create_entry(
                title="Legrand Energy",
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_CLIENT_ID): str,
                vol.Required(CONF_CLIENT_SECRET): str,
                vol.Required(CONF_SUBSCRIPTION_KEY): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @callback
    def async_get_options_flow(self, config_entry):
        return LegrandEnergyOptionsFlow(config_entry)


class LegrandEnergyOptionsFlow(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return self.async_create_entry(title="", data={})
