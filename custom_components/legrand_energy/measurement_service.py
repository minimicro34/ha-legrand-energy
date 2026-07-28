"""Electricity measurement orchestration service."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.util import dt as dt_util

from .contract_models import Contract
from .helpers.measurement_processor import MeasurementProcessor
from .helpers.private_measure_decoder import decode_energy_points_by_module
from .models import (
    LegrandEnergyData,
    LegrandMeasurements,
    LegrandModule,
    LegrandProjections,
)
from .private_api import (
    LegrandPrivateApi,
    LegrandPrivateApiAuthenticationError,
    LegrandPrivateApiError,
    LegrandPrivateApiRateLimitError,
)
from .tariff_engine import TariffEngine

_LOGGER = logging.getLogger(__name__)


class MeasurementService:
    """Fetch and process electricity measurements."""

    def __init__(self, private_api: LegrandPrivateApi) -> None:
        """Initialize the measurement service."""
        self._private_api = private_api

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
        LegrandProjections | None,
    ]:
        """Fetch and calculate measurements for every electricity module."""
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
            raw = await self._private_api.get_electricity_measures(
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

        except (
            LegrandPrivateApiAuthenticationError,
            LegrandPrivateApiRateLimitError,
        ):
            raise

        except LegrandPrivateApiError as err:
            _LOGGER.warning(
                "Unable to update private measurements, keeping cached data: %s",
                err,
            )

            if previous_data is not None:
                return (
                    previous_data.measurements,
                    previous_data.measurements_by_module,
                    previous_data.projections,
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

        measurements_by_module: dict[str, LegrandMeasurements] = {}

        for module_id, points in points_by_module.items():
            MeasurementProcessor.apply_tariffs(
                points=points,
                tariff_engine=tariff_engine,
            )

            today_points = MeasurementProcessor.points_since(points, today_start)
            week_points = MeasurementProcessor.points_since(points, week_start)
            month_points = MeasurementProcessor.points_since(points, month_start)
            year_points = MeasurementProcessor.points_since(points, year_start)

            if not today_points:
                continue

            measurements_by_module[module_id] = MeasurementProcessor.build_measurements(
                today_points=today_points,
                week_points=week_points,
                month_points=month_points,
                year_points=year_points,
                peak_price=peak_price,
                off_peak_price=off_peak_price,
            )

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

        return measurements, measurements_by_module, projections
