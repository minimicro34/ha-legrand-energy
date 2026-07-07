"""DataUpdateCoordinator for Legrand Energy."""

from __future__ import annotations

import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LegrandEnergyApi, LegrandEnergyApiError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .models import LegrandModule
from .parser import parse_energy_measure
from .private_api import LegrandPrivateApi, LegrandPrivateApiError

_LOGGER = logging.getLogger(__name__)


class LegrandEnergyCoordinator(DataUpdateCoordinator[dict[str, LegrandModule]]):
    """Legrand Energy coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        self.entry = entry
        self.hass = hass

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

        session = async_get_clientsession(hass)

        self.api = LegrandEnergyApi(
            session=session,
            access_token=entry.data["access_token"],
            refresh_token=entry.data["refresh_token"],
            client_id=entry.data["client_id"],
            client_secret=entry.data["client_secret"],
            token_update_callback=update_tokens,
        )

        web_token = entry.data.get("web_token")
        self.private_api = (
            LegrandPrivateApi(session=session, web_token=web_token)
            if web_token
            else None
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, LegrandModule]:
        """Fetch data from APIs."""
        try:
            modules = await self.api.update()

            if self.private_api is not None:
                await self._update_private_measures(modules)

            return modules

        except LegrandEnergyApiError as err:
            raise UpdateFailed(f"Legrand Energy update failed: {err}") from err

    async def _update_private_measures(
        self,
        modules: dict[str, LegrandModule],
    ) -> None:
        """Update private electricity measures."""
        if self.private_api is None:
            return

        home_id = self._get_home_id()
        if home_id is None:
            return

        now = int(time.time())
        date_end = now
        date_begin = now - 24 * 60 * 60

        for module in modules.values():
            if module.bridge is None:
                continue

            # Pour l'instant, on ne traite que les circuits électriques #0 à #5.
            try:
                suffix = int(module.id.rsplit("#", 1)[1])
            except (IndexError, ValueError):
                continue

            if suffix > 5:
                continue

            try:
                raw = await self.private_api.get_electricity_measure(
                    home_id=home_id,
                    module_id=module.id,
                    bridge=module.bridge,
                    date_begin=date_begin,
                    date_end=date_end,
                )
            except LegrandPrivateApiError as err:
                _LOGGER.debug(
                    "Private measure failed for %s: %s",
                    module.id,
                    err,
                )
                continue

            measure = parse_energy_measure(raw)

            module.energy_tariff1 = measure.energy_tariff1
            module.energy_tariff2 = measure.energy_tariff2
            module.price_tariff1 = measure.price_tariff1
            module.price_tariff2 = measure.price_tariff2
            module.last_measure = measure.timestamp

    def _get_home_id(self) -> str | None:
        """Return first home id from cached homesdata."""
        homesdata = self.api._homes_cache  # noqa: SLF001

        if not homesdata:
            return None

        homes = homesdata.get("body", {}).get("homes", [])
        if not homes:
            return None

        return homes[0].get("id")