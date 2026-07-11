"""Data update coordinator for Legrand Energy."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    LegrandEnergyApi,
    LegrandEnergyApiError,
    LegrandEnergyAuthenticationError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .contract_models import Contract
from .contract_parser import parse_contract
from .helpers.daily_statistics import compute_daily_statistics
from .helpers.private_measure_decoder import decode_energy_points
from .helpers.projections import project_today
from .models import (
    LegrandEnergyData,
    LegrandMeasurements,
    LegrandModule,
    LegrandProjections,
)
from .private_api import LegrandPrivateApi, LegrandPrivateApiError
from .tariff_engine import TariffEngine, TariffState

_LOGGER = logging.getLogger(__name__)


class LegrandEnergyCoordinator(DataUpdateCoordinator[LegrandEnergyData]):
    """Coordinate Legrand Energy API updates."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: LegrandEnergyApi,
        private_api: LegrandPrivateApi | None = None,
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
        self.private_api = private_api

    async def _async_update_data(self) -> LegrandEnergyData:
        """Fetch and assemble the latest Legrand Energy data."""
        try:
            modules = await self.api.discover_modules()
            contract: Contract | None = None
            tariff: TariffState | None = None
            measurements: LegrandMeasurements | None = None
            projections: LegrandProjections | None = None

            home_id = self._get_home_id()
            if self.private_api is not None and home_id is not None:
                contract = await self._async_get_contract(home_id)

                engine = TariffEngine(contract) if contract is not None else None
                if engine is not None:
                    try:
                        tariff = engine.current_state(dt_util.now())
                    except ValueError as err:
                        _LOGGER.warning("Unable to determine current tariff: %s", err)

                total_module = self._find_total_module(modules)
                if total_module is not None:
                    measurements, projections = await self._async_get_measurements(
                        home_id,
                        total_module,
                        contract,
                        engine,
                    )

            return LegrandEnergyData(
                modules=modules,
                contract=contract,
                tariff=tariff,
                measurements=measurements,
                projections=projections,
            )

        except LegrandEnergyAuthenticationError as err:
            raise ConfigEntryAuthFailed("Legrand Energy authentication failed") from err
        except LegrandEnergyApiError as err:
            raise UpdateFailed(f"Unable to update Legrand Energy data: {err}") from err

    async def _async_get_contract(self, home_id: str) -> Contract | None:
        """Fetch and parse the electricity contract."""
        if self.private_api is None:
            return None

        try:
            raw = await self.private_api.getcontracts(home_id)
        except LegrandPrivateApiError as err:
            _LOGGER.warning("Unable to update electricity contract: %s", err)
            return None

        return parse_contract(raw)

    async def _async_get_measurements(
        self,
        home_id: str,
        module: LegrandModule,
        contract: Contract | None,
        engine: TariffEngine | None,
    ) -> tuple[LegrandMeasurements | None, LegrandProjections | None]:
        """Fetch measurements for the total electricity module."""
        if self.private_api is None or module.bridge is None:
            return None, None

        now = dt_util.now()
        date_end = int(now.timestamp())
        date_begin = date_end - 24 * 60 * 60

        try:
            raw = await self.private_api.get_electricity_measure(
                home_id=home_id,
                module_id=module.id,
                bridge=module.bridge,
                date_begin=date_begin,
                date_end=date_end,
            )
        except LegrandPrivateApiError as err:
            _LOGGER.warning("Unable to update private measurements: %s", err)
            return None, None

        points = decode_energy_points(raw)
        if not points:
            return None, None

        if engine is not None:
            for point in points:
                try:
                    state = engine.state_at(dt_util.as_local(point.timestamp))
                except ValueError:
                    continue
                point.tariff = state.zone_name
                point.zone_id = state.zone_id

        today_points = [
            point
            for point in points
            if dt_util.as_local(point.timestamp).date() == now.date()
        ]

        peak_price = contract.peak_price if contract and contract.peak_price else 0.0
        off_peak_price = (
            contract.off_peak_price if contract and contract.off_peak_price else 0.0
        )
        daily = compute_daily_statistics(today_points, peak_price, off_peak_price)
        projection = project_today(daily.total_energy, daily.total_cost, now)

        measurements = LegrandMeasurements(
            energy_today=daily.total_energy / 1000,
            cost_today=daily.total_cost,
        )
        projections = LegrandProjections(
            energy_end_of_day=projection.projected_energy / 1000,
            cost_end_of_day=projection.projected_cost,
        )
        return measurements, projections

    def _get_home_id(self) -> str | None:
        """Return the first home ID from cached topology data."""
        homesdata = self.api._homes_cache  # noqa: SLF001
        if homesdata is None:
            return None

        homes = homesdata.get("body", {}).get("homes", [])
        if not isinstance(homes, list) or not homes:
            return None

        home = homes[0]
        if not isinstance(home, dict):
            return None

        home_id = home.get("id")
        return home_id if isinstance(home_id, str) else None

    @staticmethod
    def _find_total_module(
        modules: dict[str, LegrandModule],
    ) -> LegrandModule | None:
        """Return the total electricity module, when available."""
        circuits = [module for module in modules.values() if module.bridge is not None]

        for module in circuits:
            if module.id.endswith("#5"):
                return module

        for module in circuits:
            if module.name.casefold() == "total":
                return module

        return circuits[0] if circuits else None
