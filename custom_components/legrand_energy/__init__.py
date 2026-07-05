"""Legrand Energy integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_SUBSCRIPTION_KEY
from .api import LegrandAPI
from .coordinator import LegrandEnergyCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Legrand Energy from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    client_id = entry.data[CONF_CLIENT_ID]
    client_secret = entry.data[CONF_CLIENT_SECRET]
    subscription_key = entry.data[CONF_SUBSCRIPTION_KEY]

    # ⚠️ TEMPORAIRE (sera remplacé par OAuth Home Assistant)
    access_token = entry.data.get("access_token")

    if not access_token:
        _LOGGER.error("Missing access_token - OAuth not implemented yet")
        raise ConfigEntryNotReady("Missing OAuth token")

    api = LegrandAPI(
        access_token=access_token,
        subscription_key=subscription_key,
    )

    # -------------------------
    # Fetch homes to get home_id
    # -------------------------
    try:
        homes = await api.async_get_homesdata()
        homes_list = homes.get("body", {}).get("homes", [])

        if not homes_list:
            raise ConfigEntryNotReady("No homes found")

        home_id = homes_list[0]["id"]

    except Exception as err:
        _LOGGER.error("Failed to fetch homesdata: %s", err)
        raise ConfigEntryNotReady from err

    # -------------------------
    # Create coordinator
    # -------------------------
    coordinator = LegrandEnergyCoordinator(
        hass=hass,
        api=api,
        home_id=home_id,
    )

    await coordinator.async_config_entry_first_refresh()

    # Store runtime data
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "home_id": home_id,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload integration."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
