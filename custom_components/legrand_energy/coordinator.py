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
from .helpers.private_measure_decoder import decode_energy_points_by_module
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

SECONDS_PER_DAY = 24 * 60 * 60


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
            measurements_by_module: dict[str, LegrandMeasurements] = {}
            projections: LegrandProjections | None = None

            home_id = self._get_home_id()

            if self.private_api is not None and home_id is not None:
                contract = await self._async_get_contract(home_id)

                tariff_engine = TariffEngine(contract) if contract is not None else None

                if tariff_engine is not None:
                    try:
                        tariff = tariff_engine.current_state(dt_util.now())
                    except ValueError as err:
                        _LOGGER.warning(
                            "Unable to determine current tariff: %s",
                            err,
                        )

                (
                    measurements,
                    measurements_by_module,
                    projections,
                ) = await self._async_get_all_measurements(
                    home_id=home_id,
                    modules=modules,
                    contract=contract,
                    tariff_engine=tariff_engine,
                )

            return LegrandEnergyData(
                modules=modules,
                contract=contract,
                tariff=tariff,
                measurements=measurements,
                measurements_by_module=measurements_by_module,
                projections=projections,
            )

        except LegrandEnergyAuthenticationError as err:
            raise ConfigEntryAuthFailed("Legrand Energy authentication failed") from err

        except LegrandEnergyApiError as err:
            raise UpdateFailed(f"Unable to update Legrand Energy data: {err}") from err

    async def _async_get_contract(
        self,
        home_id: str,
    ) -> Contract | None:
        """Fetch and parse the electricity contract."""
        if self.private_api is None:
            return None

        try:
            raw = await self.private_api.getcontracts(home_id)
        except LegrandPrivateApiError as err:
            _LOGGER.warning(
                "Unable to update electricity contract: %s",
                err,
            )
            return None

        return parse_contract(raw)

    async def _async_get_all_measurements(
        self,
        home_id: str,
        modules: dict[str, LegrandModule],
        contract: Contract | None,
        tariff_engine: TariffEngine | None,
    ) -> tuple[
        LegrandMeasurements | None,
        dict[str, LegrandMeasurements],
        LegrandProjections | None,
    ]:
        """Fetch measurements for all electricity circuits."""
        if self.private_api is None:
            return None, {}, None

        circuits = [module for module in modules.values() if module.bridge is not None]

        if not circuits:
            return None, {}, None

        now = dt_util.now()
        date_end = int(now.timestamp())
        date_begin = date_end - SECONDS_PER_DAY

        _LOGGER.warning(
            "Requesting measurements for modules: %s",
            [module.id for module in circuits],
        )

        try:
            raw = await self.private_api.get_electricity_measures(
                home_id=home_id,
                modules=[
                    (module.id, module.bridge)
                    for module in circuits
                    if module.bridge is not None
                ],
                date_begin=date_begin,
                date_end=date_end,
            )
        except LegrandPrivateApiError as err:
            _LOGGER.warning(
                "Unable to update private measurements: %s",
                err,
            )
            return None, {}, None

        points_by_module = decode_energy_points_by_module(raw)
        _LOGGER.warning(
            "Measurements returned for modules: %s",
            {module_id: len(points) for module_id, points in points_by_module.items()},
        )
        measurements_by_module: dict[str, LegrandMeasurements] = {}

        peak_price = (
            contract.peak_price
            if contract is not None and contract.peak_price is not None
            else 0.0
        )

        off_peak_price = (
            contract.off_peak_price
            if contract is not None and contract.off_peak_price is not None
            else 0.0
        )

        for module_id, points in points_by_module.items():
            if tariff_engine is not None:
                for point in points:
                    try:
                        state = tariff_engine.state_at(
                            dt_util.as_local(point.timestamp)
                        )
                    except ValueError:
                        continue

                    point.tariff = state.zone_name
                    point.zone_id = state.zone_id

            today_points = [
                point
                for point in points
                if dt_util.as_local(point.timestamp).date() == now.date()
            ]

            if not today_points:
                continue

            daily = compute_daily_statistics(
                today_points,
                peak_price,
                off_peak_price,
            )

            measurements_by_module[module_id] = LegrandMeasurements(
                energy_today=daily.total_energy / 1000,
                cost_today=daily.total_cost,
            )

        total_module = self._find_total_module(modules)

        measurements = (
            measurements_by_module.get(total_module.id)
            if total_module is not None
            else None
        )

        projections: LegrandProjections | None = None

        if measurements is not None:
            projection = project_today(
                (measurements.energy_today or 0.0) * 1000,
                measurements.cost_today or 0.0,
                now,
            )

            projections = LegrandProjections(
                energy_end_of_day=projection.projected_energy / 1000,
                cost_end_of_day=projection.projected_cost,
            )

        return (
            measurements,
            measurements_by_module,
            projections,
        )

    def _get_home_id(self) -> str | None:
        """Return the first home ID from cached topology data."""
        homesdata = self.api._homes_cache  # noqa: SLF001

        if homesdata is None:
            return None

        body = homesdata.get("body")
        if not isinstance(body, dict):
            return None

        homes = body.get("homes")
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
        """Return the total electricity module."""
        circuits = [module for module in modules.values() if module.bridge is not None]

        for module in circuits:
            if module.id.endswith("#5"):
                return module

        for module in circuits:
            if module.name.casefold() == "total":
                return module

        return circuits[0] if circuits else None
