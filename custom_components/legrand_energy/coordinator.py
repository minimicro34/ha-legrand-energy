"""DataUpdateCoordinator for Legrand Energy."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LegrandEnergyApi, LegrandEnergyApiError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .models import LegrandModule

_LOGGER = logging.getLogger(__name__)


class LegrandEnergyCoordinator(DataUpdateCoordinator[dict[str, LegrandModule]]):
    """Legrand Energy coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        self.entry = entry

        async def update_tokens(access_token: str, refresh_token: str) -> None:
            """Persist refreshed OAuth tokens."""
            hass.config_entries.async_update_entry(
                entry,
                data={
                    **entry.data,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                },
            )

        self.api = LegrandEnergyApi(
            session=async_get_clientsession(hass),
            access_token=entry.data["access_token"],
            refresh_token=entry.data["refresh_token"],
            client_id=entry.data["client_id"],
            client_secret=entry.data["client_secret"],
            token_update_callback=update_tokens,
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, LegrandModule]:
        """Fetch data from API."""
        try:
            return await self.api.update()
        except LegrandEnergyApiError as err:
            raise UpdateFailed(f"Legrand Energy update failed: {err}") from err