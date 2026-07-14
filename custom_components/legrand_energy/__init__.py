"""The Legrand Energy integration."""

from __future__ import annotations

from typing import Any
from urllib.parse import unquote

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LegrandEnergyApi
from .coordinator import LegrandEnergyCoordinator
from .private_api import LegrandPrivateApi

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]

PRIVATE_AUTH_KEYS = (
    "web_token",
    "refresh_token_web",
    "laravel_session",
    "mail_cookie",
    "authorize_state",
    "xsrf_token",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Legrand Energy from a config entry."""
    session = async_get_clientsession(hass)

    async def async_update_tokens(
        access_token: str,
        refresh_token: str,
    ) -> None:
        """Store refreshed public OAuth tokens."""
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                "access_token": access_token,
                "refresh_token": refresh_token,
            },
        )

    async def async_update_private_auth(
        auth_data: dict[str, str],
    ) -> None:
        """Persist refreshed private Netatmo authentication data."""
        new_data: dict[str, Any] = dict(entry.data)
        new_data.update(auth_data)

        new_options: dict[str, Any] = dict(entry.options)
        new_options.update(auth_data)

        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            options=new_options,
        )

    # API publique
    api = LegrandEnergyApi(
        session=session,
        access_token=entry.data["access_token"],
        refresh_token=entry.data["refresh_token"],
        client_id=entry.data["client_id"],
        client_secret=entry.data["client_secret"],
        token_update_callback=async_update_tokens,
    )

    # Lecture des identifiants de l'API privée
    def private_value(key: str) -> str | None:
        """Return private authentication value."""
        option_value = entry.options.get(key)

        if isinstance(option_value, str) and option_value:
            return unquote(option_value)

        data_value = entry.data.get(key)

        return (
            unquote(data_value) if isinstance(data_value, str) and data_value else None
        )

    # API privée
    web_token = private_value("web_token")

    private_api = (
        LegrandPrivateApi(
            session=session,
            web_token=web_token,
            refresh_token=private_value("refresh_token_web"),
            laravel_session=private_value("laravel_session"),
            mail_cookie=private_value("mail_cookie"),
            authorize_state=private_value("authorize_state"),
            xsrf_token=private_value("xsrf_token"),
            auth_update_callback=async_update_private_auth,
        )
        if web_token is not None
        else None
    )

    # Coordinator
    coordinator = LegrandEnergyCoordinator(
        hass=hass,
        config_entry=entry,
        api=api,
        private_api=private_api,
    )

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    async def async_entry_updated(
        hass: HomeAssistant,
        updated_entry: ConfigEntry,
    ) -> None:
        """Apply user-updated options and reload the integration."""
        new_data: dict[str, Any] = dict(updated_entry.data)

        for key in PRIVATE_AUTH_KEYS:
            option_value = updated_entry.options.get(key)

            if isinstance(option_value, str):
                if option_value:
                    new_data[key] = option_value
                else:
                    new_data.pop(key, None)

        if new_data != updated_entry.data:
            hass.config_entries.async_update_entry(
                updated_entry,
                data=new_data,
            )

        await hass.config_entries.async_reload(updated_entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(async_entry_updated))

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload a Legrand Energy config entry."""
    return await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )
