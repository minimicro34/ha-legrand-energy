"""The Legrand Energy integration."""

from __future__ import annotations

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


async def async_update_options(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


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
        """Store refreshed OAuth tokens."""
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                "access_token": access_token,
                "refresh_token": refresh_token,
            },
        )

    api = LegrandEnergyApi(
        session=session,
        access_token=entry.data["access_token"],
        refresh_token=entry.data["refresh_token"],
        client_id=entry.data["client_id"],
        client_secret=entry.data["client_secret"],
        token_update_callback=async_update_tokens,
    )

    web_token = entry.options.get("web_token", entry.data.get("web_token"))
    private_api = (
        LegrandPrivateApi(session=session, web_token=web_token)
        if isinstance(web_token, str) and web_token
        else None
    )

    coordinator = LegrandEnergyCoordinator(
        hass=hass,
        config_entry=entry,
        api=api,
        private_api=private_api,
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload a Legrand Energy config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
