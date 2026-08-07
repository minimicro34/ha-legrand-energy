"""Electricity and fluid measurement orchestration service."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from homeassistant.util import dt as dt_util

from .helpers.energy_series import EnergyPoint
from .helpers.fluid_measurement_processor import FluidMeasurementProcessor
from .helpers.measurement_processor import MeasurementProcessor
from .helpers.private_measure_decoder import decode_points_by_module
from .helpers.retry_backoff import RetryBackoff
from .models import (
    FluidMeasurements,
    LegrandEnergyData,
    LegrandMeasurements,
    LegrandModule,
    LegrandProjections,
)
from .models.contract import Contract
from .models.fluid import FluidType
from .private_api import (
    LegrandPrivateApi,
    LegrandPrivateApiAuthenticationError,
    LegrandPrivateApiError,
    LegrandPrivateApiRateLimitError,
)
from .tariff_engine import TariffEngine

_LOGGER = logging.getLogger(__name__)

HISTORICAL_RETRY_DELAYS = (timedelta(minutes=15),)

CURRENT_DAY_RETRY_DELAYS = (
    timedelta(minutes=2),
    timedelta(minutes=5),
    timedelta(minutes=10),
    timedelta(minutes=15),
)


class MeasurementService:
    """Fetch and process electricity and fluid measurements."""

    def __init__(self, private_api: LegrandPrivateApi) -> None:
        """Initialize the measurement service."""
        self._private_api = private_api

        self._historical_points_by_module: dict[str, list[EnergyPoint]] = {}
        self._historical_cache_date: date | None = None
        self._historical_backoff = RetryBackoff(HISTORICAL_RETRY_DELAYS)

        self._current_day_backoff = RetryBackoff(CURRENT_DAY_RETRY_DELAYS)

    def _modules_for_fluid(
        self,
        modules: list[LegrandModule],
        fluid_type: FluidType,
    ) -> list[tuple[str, str]]:
        """Return module payload for a specific fluid type."""
        return [
            (module.id, module.bridge)
            for module in modules
            if module.bridge is not None and module.fluid_type is fluid_type
        ]

    async def _fetch_points_by_module(
        self,
        *,
        home_id: str,
        modules: list[tuple[str, str]],
        fluid_type: FluidType,
        date_begin: int,
        date_end: int,
        scale: str,
    ) -> dict[str, list[EnergyPoint]]:
        """Fetch and decode measurements for one fluid type."""
        if not modules:
            return {}

        raw = await self._private_api.get_fluid_measures(
            home_id=home_id,
            modules=modules,
            fluid_type=fluid_type,
            date_begin=date_begin,
            date_end=date_end,
            scale=scale,
        )

        points_by_module = decode_points_by_module(
            raw,
            fluid_type=fluid_type,
        )

        for module_id, _bridge in modules:
            points_by_module.setdefault(module_id, [])

        return points_by_module

    async def async_get_all(
        self,
        *,
        home_id: str,
        modules: dict[str, LegrandModule],
        contract: Contract | None,
        tariff_engine: TariffEngine | None,
        previous_data: LegrandEnergyData | None,
    ) -> tuple[
        LegrandMeasurements | None,
        dict[str, LegrandMeasurements],
        dict[str, FluidMeasurements],
        dict[str, FluidMeasurements],
        LegrandProjections | None,
    ]:
        """Fetch and calculate measurements for every supported module."""
        circuits = [module for module in modules.values() if module.bridge is not None]

        if not circuits:
            return None, {}, {}, {}, None

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

        electricity_modules = self._modules_for_fluid(
            circuits,
            FluidType.ELECTRICITY,
        )
        water_modules = self._modules_for_fluid(
            circuits,
            FluidType.WATER,
        )
        gas_modules = self._modules_for_fluid(
            circuits,
            FluidType.GAS,
        )

        fluid_module_groups = (
            (FluidType.ELECTRICITY, electricity_modules),
            (FluidType.WATER, water_modules),
            (FluidType.GAS, gas_modules),
        )

        if not any(fluid_modules for _fluid_type, fluid_modules in fluid_module_groups):
            return None, {}, {}, {}, None

        history_is_outdated = self._historical_cache_date != today_start.date()

        if history_is_outdated and self._historical_backoff.is_ready(now):
            try:
                historical_points_by_module: dict[str, list[EnergyPoint]] = {}

                if year_start < today_start:
                    for fluid_type, fluid_modules in fluid_module_groups:
                        historical_points_by_module.update(
                            await self._fetch_points_by_module(
                                home_id=home_id,
                                modules=fluid_modules,
                                fluid_type=fluid_type,
                                date_begin=int(year_start.timestamp()),
                                date_end=int(today_start.timestamp()) - 1,
                                scale="1day",
                            )
                        )

            except (
                LegrandPrivateApiAuthenticationError,
                LegrandPrivateApiRateLimitError,
            ):
                raise

            except LegrandPrivateApiError as err:
                retry_delay = self._historical_backoff.record_failure(now)

                _LOGGER.warning(
                    "Unable to update historical private measurements, "
                    "keeping cached data and retrying in %s: %s",
                    retry_delay,
                    err,
                )

            else:
                self._historical_points_by_module = historical_points_by_module
                self._historical_cache_date = today_start.date()

                previous_failure_count = self._historical_backoff.reset()

                if previous_failure_count:
                    _LOGGER.info(
                        "Historical private measurements recovered "
                        "after %s failed update(s)",
                        previous_failure_count,
                    )

        if not self._current_day_backoff.is_ready(now):
            return self._cached_result(previous_data)

        try:
            today_points_by_module: dict[str, list[EnergyPoint]] = {}

            for fluid_type, fluid_modules in fluid_module_groups:
                today_points_by_module.update(
                    await self._fetch_points_by_module(
                        home_id=home_id,
                        modules=fluid_modules,
                        fluid_type=fluid_type,
                        date_begin=int(today_start.timestamp()),
                        date_end=int(now.timestamp()),
                        scale="5min",
                    )
                )

        except (
            LegrandPrivateApiAuthenticationError,
            LegrandPrivateApiRateLimitError,
        ):
            raise

        except LegrandPrivateApiError as err:
            retry_delay = self._current_day_backoff.record_failure(now)

            _LOGGER.warning(
                "Unable to update current-day private measurements, "
                "keeping cached data and retrying in %s: %s",
                retry_delay,
                err,
            )

            return self._cached_result(previous_data)

        previous_failure_count = self._current_day_backoff.reset()

        if previous_failure_count:
            _LOGGER.info(
                "Current-day private measurements recovered after %s failed update(s)",
                previous_failure_count,
            )

        historical_points = self._historical_points_by_module

        points_by_module = {
            module_id: sorted(
                historical_points.get(module_id, [])
                + today_points_by_module.get(module_id, []),
                key=lambda point: point.timestamp,
            )
            for module_id in historical_points.keys() | today_points_by_module.keys()
        }

        if contract is None:
            peak_price = 0.0
            off_peak_price = 0.0
        else:
            peak_price = contract.peak_price or 0.0
            off_peak_price = contract.off_peak_price or 0.0

        measurements_by_module: dict[str, LegrandMeasurements] = {}
        water_measurements_by_module: dict[str, FluidMeasurements] = {}
        gas_measurements_by_module: dict[str, FluidMeasurements] = {}

        for module_id, points in points_by_module.items():
            module = modules.get(module_id)

            if module is None:
                continue

            if module.fluid_type is FluidType.ELECTRICITY:
                MeasurementProcessor.apply_tariffs(
                    points=points,
                    tariff_engine=tariff_engine,
                )

                today_points = MeasurementProcessor.points_since(
                    points,
                    today_start,
                )
                week_points = MeasurementProcessor.points_since(
                    points,
                    week_start,
                )
                month_points = MeasurementProcessor.points_since(
                    points,
                    month_start,
                )
                year_points = MeasurementProcessor.points_since(
                    points,
                    year_start,
                )

                if not today_points:
                    previous_measurements = (
                        previous_data.measurements_by_module.get(module_id)
                        if previous_data is not None
                        else None
                    )

                    if previous_measurements is not None:
                        measurements_by_module[module_id] = previous_measurements

                    continue

                measurements_by_module[module_id] = (
                    MeasurementProcessor.build_measurements(
                        today_points=today_points,
                        week_points=week_points,
                        month_points=month_points,
                        year_points=year_points,
                        peak_price=peak_price,
                        off_peak_price=off_peak_price,
                    )
                )

            today_points = FluidMeasurementProcessor.points_since(
                points,
                today_start,
            )
            week_points = FluidMeasurementProcessor.points_since(
                points,
                week_start,
            )
            month_points = FluidMeasurementProcessor.points_since(
                points,
                month_start,
            )
            year_points = FluidMeasurementProcessor.points_since(
                points,
                year_start,
            )

            fluid_measurements = FluidMeasurementProcessor.build_measurements(
                today_points=today_points,
                week_points=week_points,
                month_points=month_points,
                year_points=year_points,
            )

            if module.fluid_type is FluidType.WATER:
                water_measurements_by_module[module_id] = fluid_measurements
            else:
                gas_measurements_by_module[module_id] = fluid_measurements

        total_module = MeasurementProcessor.find_total_module(modules)

        measurements = (
            measurements_by_module.get(total_module.id)
            if total_module is not None
            else None
        )

        projections = (
            MeasurementProcessor.build_projections(
                measurements=measurements,
                now=now,
            )
            if measurements is not None
            else None
        )

        return (
            measurements,
            measurements_by_module,
            water_measurements_by_module,
            gas_measurements_by_module,
            projections,
        )

    @staticmethod
    def _cached_result(
        previous_data: LegrandEnergyData | None,
    ) -> tuple[
        LegrandMeasurements | None,
        dict[str, LegrandMeasurements],
        dict[str, FluidMeasurements],
        dict[str, FluidMeasurements],
        LegrandProjections | None,
    ]:
        """Return previously cached measurements when available."""
        if previous_data is None:
            return None, {}, {}, {}, None

        return (
            previous_data.measurements,
            previous_data.measurements_by_module,
            previous_data.water_measurements_by_module,
            previous_data.gas_measurements_by_module,
            previous_data.projections,
        )
