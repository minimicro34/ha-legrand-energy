"""Fluid measurement processing helpers."""

from __future__ import annotations

from datetime import datetime

from ..models import FluidMeasurements
from .energy_series import EnergyPoint


class FluidMeasurementProcessor:
    """Calculate water and gas consumption totals."""

    @staticmethod
    def points_since(
        points: list[EnergyPoint],
        start: datetime,
    ) -> list[EnergyPoint]:
        """Return points whose timestamps are on or after the start time."""
        return [point for point in points if point.timestamp >= start]

    @staticmethod
    def build_measurements(
        *,
        today_points: list[EnergyPoint],
        week_points: list[EnergyPoint],
        month_points: list[EnergyPoint],
        year_points: list[EnergyPoint],
    ) -> FluidMeasurements:
        """Build consumption and cost totals for one fluid module."""
        return FluidMeasurements(
            consumption_today=FluidMeasurementProcessor._sum_consumption(today_points),
            consumption_week=FluidMeasurementProcessor._sum_consumption(week_points),
            consumption_month=FluidMeasurementProcessor._sum_consumption(month_points),
            consumption_year=FluidMeasurementProcessor._sum_consumption(year_points),
            cost_today=FluidMeasurementProcessor._sum_cost(today_points),
            cost_week=FluidMeasurementProcessor._sum_cost(week_points),
            cost_month=FluidMeasurementProcessor._sum_cost(month_points),
            cost_year=FluidMeasurementProcessor._sum_cost(year_points),
        )

    @staticmethod
    def _sum_consumption(points: list[EnergyPoint]) -> float:
        """Return the sum of available consumption values."""
        return sum(point.energy for point in points)

    @staticmethod
    def _sum_cost(points: list[EnergyPoint]) -> float:
        """Return the sum of available cost values."""
        return sum(point.price for point in points if point.price is not None)
