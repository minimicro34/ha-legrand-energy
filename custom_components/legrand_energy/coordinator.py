"""Data coordinator for Legrand Energy."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LegrandEnergyApi, LegrandEnergyApiError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class LegrandEnergyCoordinator(DataUpdateCoordinator):
    """Coordinator for Legrand Energy data."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        self.entry = entry

        access_token = entry.data["token"]["access_token"]
        session = async_get_clientsession(hass)
        self.api = LegrandEnergyApi(session, access_token)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            return await self.api.async_get_all_measurements()
        except LegrandEnergyApiError as err:
            raise UpdateFailed(f"Error communicating with Legrand Energy API: {err}") from err