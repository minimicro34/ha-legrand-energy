"""Data update coordinator for Legrand Energy."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import (
    LegrandEnergyApi,
    LegrandEnergyApiError,
    LegrandEnergyAuthenticationError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .models import LegrandEnergyData

_LOGGER = logging.getLogger(__name__)


class LegrandEnergyCoordinator(DataUpdateCoordinator[LegrandEnergyData]):
    """Coordinate Legrand Energy API updates."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: LegrandEnergyApi,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

        self.api = api

    async def _async_update_data(self) -> LegrandEnergyData:
        """Fetch and assemble the latest Legrand Energy data."""
        try:
            modules = await self.api.discover_modules()

            return LegrandEnergyData(
                modules=modules,
            )

        except LegrandEnergyAuthenticationError as err:
            raise ConfigEntryAuthFailed("Legrand Energy authentication failed") from err

        except LegrandEnergyApiError as err:
            raise UpdateFailed(f"Unable to update Legrand Energy data: {err}") from err
