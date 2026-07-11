"""Data update coordinator for Legrand Energy."""

from __future__ import annotations

import logging
from calendar import monthrange
from datetime import datetime, timedelta

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
from .helpers.energy_series import EnergyPoint
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
                # TEMPORARY: test possible TIC power measure types.
                for measure_type in (
                    "power",
                    "power_current",
                    "apparent_power",
                    "instantaneous_power",
                    "papp",
                    "sinsts",
                ):
                    _LOGGER.warning("POWER TEST START %s", measure_type)

                    try:
                        result = await self.private_api.get_measure(
                            home_id=home_id,
                            module_id="00:04:74:12:24:d4",
                            measure_type=measure_type,
                        )
                        _LOGGER.warning(
                            "POWER TEST %s: %s",
                            measure_type,
                            result,
                        )
                    except Exception as err:  # noqa: BLE001
                        _LOGGER.warning(
                            "POWER TEST %s exception %s: %s",
                            measure_type,
                            type(err).__name__,
                            err,
                        )

                contract = await self._async_get_contract(home_id)

            if self.private_api is not None and home_id is not None:
                homestatus = await self.private_api.homestatus(home_id)
                _LOGGER.warning("PRIVATE HOMESTATUS: %s", homestatus)

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
        """Fetch and calculate measurements for every electricity module."""
        if self.private_api is None:
            return None, {}, None

        circuits = [module for module in modules.values() if module.bridge is not None]

        if not circuits:
            return None, {}, None

        now = dt_util.now()

        today_start = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        week_start = today_start - timedelta(days=today_start.weekday())

        month_start = today_start.replace(day=1)

        year_start = today_start.replace(
            month=1,
            day=1,
        )

        try:
            raw = await self.private_api.get_electricity_measures(
                home_id=home_id,
                modules=[
                    (
                        module.id,
                        module.bridge,
                    )
                    for module in circuits
                    if module.bridge is not None
                ],
                date_begin=int(today_start.timestamp()),
                date_end=int(now.timestamp()),
            )

        except LegrandPrivateApiError as err:
            _LOGGER.warning(
                "Unable to update private measurements: %s",
                err,
            )
            return None, {}, None

        points_by_module = decode_energy_points_by_module(raw)

        peak_price = (
            contract.peak_price
            if (contract is not None and contract.peak_price is not None)
            else 0.0
        )

        off_peak_price = (
            contract.off_peak_price
            if (contract is not None and contract.off_peak_price is not None)
            else 0.0
        )

        measurements_by_module: dict[
            str,
            LegrandMeasurements,
        ] = {}

        for module_id, points in points_by_module.items():
            self._apply_tariffs(
                points=points,
                tariff_engine=tariff_engine,
            )

            today_points = self._points_since(
                points,
                today_start,
            )

            week_points = self._points_since(
                points,
                week_start,
            )

            month_points = self._points_since(
                points,
                month_start,
            )

            year_points = self._points_since(
                points,
                year_start,
            )

            if not today_points:
                continue

            measurements_by_module[module_id] = self._build_measurements(
                today_points=today_points,
                week_points=week_points,
                month_points=month_points,
                year_points=year_points,
                peak_price=peak_price,
                off_peak_price=off_peak_price,
            )

        total_module = self._find_total_module(modules)

        measurements = (
            measurements_by_module.get(total_module.id)
            if total_module is not None
            else None
        )

        projections = (
            self._build_projections(
                measurements=measurements,
                now=now,
            )
            if measurements is not None
            else None
        )

        return (
            measurements,
            measurements_by_module,
            projections,
        )

    @staticmethod
    def _apply_tariffs(
        *,
        points: list[EnergyPoint],
        tariff_engine: TariffEngine | None,
    ) -> None:
        """Assign HP or HC tariff to every measurement point."""
        if tariff_engine is None:
            return

        for point in points:
            try:
                state = tariff_engine.state_at(dt_util.as_local(point.timestamp))
            except ValueError:
                continue

            point.tariff = "HC" if state.is_off_peak else "HP"

            point.zone_id = state.zone_id

    @classmethod
    def _build_measurements(
        cls,
        *,
        today_points: list[EnergyPoint],
        week_points: list[EnergyPoint],
        month_points: list[EnergyPoint],
        year_points: list[EnergyPoint],
        peak_price: float,
        off_peak_price: float,
    ) -> LegrandMeasurements:
        """Build measurements for one electricity module."""
        energy_today_wh = cls._total_energy(today_points)

        energy_peak_today_wh = cls._energy_for_tariff(
            today_points,
            "HP",
        )

        energy_off_peak_today_wh = cls._energy_for_tariff(
            today_points,
            "HC",
        )

        cost_peak_today = (energy_peak_today_wh / 1000) * peak_price

        cost_off_peak_today = (energy_off_peak_today_wh / 1000) * off_peak_price

        cost_today = cost_peak_today + cost_off_peak_today

        energy_week_wh = cls._total_energy(week_points)

        energy_month_wh = cls._total_energy(month_points)

        energy_year_wh = cls._total_energy(year_points)

        cost_week = cls._calculate_cost(
            week_points,
            peak_price=peak_price,
            off_peak_price=off_peak_price,
        )

        cost_month = cls._calculate_cost(
            month_points,
            peak_price=peak_price,
            off_peak_price=off_peak_price,
        )

        cost_year = cls._calculate_cost(
            year_points,
            peak_price=peak_price,
            off_peak_price=off_peak_price,
        )

        return LegrandMeasurements(
            power=None,
            energy_today=(energy_today_wh / 1000),
            energy_peak_today=(energy_peak_today_wh / 1000),
            energy_off_peak_today=(energy_off_peak_today_wh / 1000),
            energy_week=(energy_week_wh / 1000),
            energy_month=(energy_month_wh / 1000),
            energy_year=(energy_year_wh / 1000),
            cost_today=cost_today,
            cost_peak_today=cost_peak_today,
            cost_off_peak_today=(cost_off_peak_today),
            cost_week=cost_week,
            cost_month=cost_month,
            cost_year=cost_year,
        )

    @staticmethod
    def _total_energy(
        points: list[EnergyPoint],
    ) -> float:
        """Return total energy in Wh."""
        return sum(point.energy for point in points)

    @staticmethod
    def _energy_for_tariff(
        points: list[EnergyPoint],
        tariff: str,
    ) -> float:
        """Return energy in Wh for a tariff."""
        return sum(point.energy for point in points if point.tariff == tariff)

    @classmethod
    def _calculate_cost(
        cls,
        points: list[EnergyPoint],
        *,
        peak_price: float,
        off_peak_price: float,
    ) -> float:
        """Calculate total cost from HP and HC energy."""
        peak_energy_wh = cls._energy_for_tariff(
            points,
            "HP",
        )

        off_peak_energy_wh = cls._energy_for_tariff(
            points,
            "HC",
        )

        return (peak_energy_wh / 1000) * peak_price + (
            off_peak_energy_wh / 1000
        ) * off_peak_price

    @classmethod
    def _build_projections(
        cls,
        *,
        measurements: LegrandMeasurements,
        now: datetime,
    ) -> LegrandProjections:
        """Build day and month projections for the main total module."""
        today_projection = project_today(
            (measurements.energy_today or 0.0) * 1000,
            measurements.cost_today or 0.0,
            now,
        )

        (
            projected_energy_month,
            projected_cost_month,
        ) = cls._project_month(
            now=now,
            energy_month=(measurements.energy_month),
            cost_month=(measurements.cost_month),
        )

        return LegrandProjections(
            energy_end_of_day=(today_projection.projected_energy / 1000),
            energy_end_of_month=(projected_energy_month),
            cost_end_of_day=(today_projection.projected_cost),
            cost_end_of_month=(projected_cost_month),
        )

    @staticmethod
    def _points_since(
        points: list[EnergyPoint],
        start: datetime,
    ) -> list[EnergyPoint]:
        """Return points at or after a local datetime."""
        return [point for point in points if dt_util.as_local(point.timestamp) >= start]

    @staticmethod
    def _project_month(
        *,
        now: datetime,
        energy_month: float | None,
        cost_month: float | None,
    ) -> tuple[
        float | None,
        float | None,
    ]:
        """Project current month totals from elapsed month time."""
        days_in_month = monthrange(
            now.year,
            now.month,
        )[1]

        seconds_today = now.hour * 3600 + now.minute * 60 + now.second

        elapsed_days = now.day - 1 + seconds_today / SECONDS_PER_DAY

        if elapsed_days <= 0:
            return None, None

        factor = days_in_month / elapsed_days

        projected_energy = energy_month * factor if energy_month is not None else None

        projected_cost = cost_month * factor if cost_month is not None else None

        return (
            projected_energy,
            projected_cost,
        )

    def _get_home_id(
        self,
    ) -> str | None:
        """Return the first home ID from cached topology data."""
        homesdata = self.api._homes_cache  # noqa: SLF001

        if homesdata is None:
            return None

        body = homesdata.get("body")

        if not isinstance(
            body,
            dict,
        ):
            return None

        homes = body.get("homes")

        if (
            not isinstance(
                homes,
                list,
            )
            or not homes
        ):
            return None

        home = homes[0]

        if not isinstance(
            home,
            dict,
        ):
            return None

        home_id = home.get("id")

        return (
            home_id
            if isinstance(
                home_id,
                str,
            )
            else None
        )

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
