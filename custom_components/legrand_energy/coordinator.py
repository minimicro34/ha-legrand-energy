"""DataUpdateCoordinator for Legrand Energy."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .api import LegrandAPI, LegrandAPIError

_LOGGER = logging.getLogger(__name__)


class LegrandEnergyCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch Legrand Energy data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: LegrandAPI,
        home_id: str,
    ) -> None:
        """Initialize coordinator."""

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{home_id}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

        self.api = api
        self.home_id = home_id

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""

        try:
            _LOGGER.debug("Fetching Legrand Energy data for home %s", self.home_id)

            homesdata = await self.api.async_get_homesdata()
            topology = await self.api.async_get_hometopology(self.home_id)
            status = await self.api.async_get_homestatus(self.home_id)
            energy = await self.api.async_get_energy(self.home_id)

            return {
                "homesdata": homesdata,
                "topology": topology,
                "status": status,
                "energy": energy,
            }

        except LegrandAPIError as err:
            _LOGGER.error("Error updating Legrand Energy data: %s", err)
            raise UpdateFailed(str(err)) from err
