"""Authentication persistence for Legrand Energy."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .models.auth import PrivateSession

PRIVATE_COOKIE_NAMES = {
    "refresh_token_web": "authnetatmocomrefresh_token",
    "laravel_session": "authnetatmocomlaravel_session",
    "mail_cookie": "authnetatmocommail_cookie",
    "authorize_state": "authnetatmocomauthorize_state",
    "xsrf_token": "XSRF-TOKEN",
}


class ConfigEntryAuthenticationStore:
    """Persist authentication sessions in a Home Assistant config entry."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the authentication store."""
        self._hass = hass
        self._entry = entry

    async def async_save_private(self, session: PrivateSession) -> None:
        """Persist the current private authentication session."""
        auth_data = {
            "web_token": session.web_token,
        }

        for config_key, cookie_name in PRIVATE_COOKIE_NAMES.items():
            cookie_value = session.cookies.get(cookie_name)

            if cookie_value is not None:
                auth_data[config_key] = cookie_value

        new_data: dict[str, Any] = dict(self._entry.data)
        new_data.update(auth_data)

        new_options: dict[str, Any] = dict(self._entry.options)
        new_options.update(auth_data)

        self._hass.config_entries.async_update_entry(
            self._entry,
            data=new_data,
            options=new_options,
        )
