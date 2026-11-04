"""Authenticated WebSocket access to cached Netatmo energy intervals."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import (
    async_response,
    websocket_command,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import LegrandEnergyCoordinator


@websocket_command(
    {
        vol.Required("type"): "legrand_energy/cached_history",  # type: ignore[dict-item]
        vol.Required("entry_id"): str,  # type: ignore[dict-item]
        vol.Required("start"): str,  # type: ignore[dict-item]
        vol.Required("end"): str,  # type: ignore[dict-item]
    }
)
@async_response
async def async_cached_history(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return bounded cached measurements without calling the private API."""
    entry_id = str(msg["entry_id"])
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        connection.send_error(msg["id"], "not_found", "Legrand Energy entry not found")
        return

    start = dt_util.parse_datetime(str(msg["start"]))
    end = dt_util.parse_datetime(str(msg["end"]))
    if (
        start is None
        or end is None
        or start.tzinfo is None
        or end.tzinfo is None
        or not start < end
        or (end - start).total_seconds() > 366 * 86400
    ):
        connection.send_error(msg["id"], "invalid_range", "Invalid history date range")
        return

    coordinator = getattr(entry, "runtime_data", None)
    if not isinstance(coordinator, LegrandEnergyCoordinator):
        connection.send_error(msg["id"], "not_ready", "Legrand Energy is not ready")
        return

    rows = coordinator.cached_energy_history(start=start, end=end)
    connection.send_result(msg["id"], {"points": rows})


def async_register(hass: HomeAssistant) -> None:
    """Register the history command once during integration setup."""
    websocket_api.async_register_command(hass, async_cached_history)
