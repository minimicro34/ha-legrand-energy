"""The Legrand Energy integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LegrandEnergyApi
from .coordinator import LegrandEnergyCoordinator

PLATFORMS = [Platform.SENSOR]


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

    coordinator = LegrandEnergyCoordinator(
        hass=hass,
        config_entry=entry,
        api=api,
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

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
