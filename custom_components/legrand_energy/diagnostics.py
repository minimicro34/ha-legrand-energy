"""Diagnostics support for Legrand Energy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .authentication_store import PRIVATE_COOKIE_NAMES
from .coordinator import LegrandEnergyCoordinator

TO_REDACT = {
    "access_token",
    "refresh_token",
    "client_secret",
    "username",
    "password",
    "web_token",
    *PRIVATE_COOKIE_NAMES.keys(),
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: LegrandEnergyCoordinator = entry.runtime_data

    return {
        "entry": async_redact_data(
            dict(entry.data),
            TO_REDACT,
        ),
        "homesdata": async_redact_data(
            await coordinator.api.homesdata(force_refresh=True),
            TO_REDACT,
        ),
    }
