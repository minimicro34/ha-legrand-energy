"""Legrand Energy integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_SUBSCRIPTION_KEY
from .api import LegrandAPI
from .coordinator import LegrandEnergyCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Legrand Energy from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    subscription_key = entry.data[CONF_SUBSCRIPTION_KEY]

    # ✅ OAuth2 session fourni par Home Assistant
    oauth_session = entry.runtime_data

    # -------------------------
    # API client
    # -------------------------
    api = LegrandAPI(
        session=oauth_session,
        subscription_key=subscription_key,
    )

    # -------------------------
    # Get homes
    # -------------------------
    homes = await api.async_get_homesdata()
    homes_list = homes.get("body", {}).get("homes", [])

    if not homes_list:
        _LOGGER.error("No homes found in API response")
        return False

    home_id = homes_list[0]["id"]

    # -------------------------
    # Coordinator
    # -------------------------
    coordinator = LegrandEnergyCoordinator(
        hass=hass,
        api=api,
        home_id=home_id,
    )

    await coordinator.async_config_entry_first_refresh()

    # -------------------------
    # Store runtime data
    # -------------------------
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "home_id": home_id,
    }

    # -------------------------
    # Forward to platforms
    # -------------------------
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload integration."""

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
