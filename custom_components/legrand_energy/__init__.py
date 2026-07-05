"""Legrand Energy integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_SUBSCRIPTION_KEY
from .api import LegrandAPI

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Legrand Energy from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    client_id = entry.data[CONF_CLIENT_ID]
    client_secret = entry.data[CONF_CLIENT_SECRET]
    subscription_key = entry.data[CONF_SUBSCRIPTION_KEY]

    # ⚠️ Pour l'instant: access_token temporaire (sera remplacé par OAuth HA)
    access_token = entry.data.get("access_token")

    if not access_token:
        _LOGGER.warning("No access_token yet - integration not fully connected")
        raise ConfigEntryNotReady(
            "OAuth not implemented yet - waiting for token flow"
        )

    api = LegrandAPI(
        access_token=access_token,
        subscription_key=subscription_key,
    )

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload integration."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
