"""Measurement processing helpers."""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime

from homeassistant.util import dt as dt_util

from ..models import (
    LegrandMeasurements,
    LegrandModule,
    LegrandProjections,
)
from ..tariff_engine import TariffEngine
from .energy_series import EnergyPoint
from .projections import project_today

SECONDS_PER_DAY = 24 * 60 * 60


class MeasurementProcessor:
    """Process electricity measurements and projections."""

    @staticmethod
    def apply_tariffs(
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
    def build_measurements(
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
        energy_today_wh = cls.total_energy(today_points)

        energy_peak_today_wh = cls.energy_for_tariff(
            today_points,
            "HP",
        )

        energy_off_peak_today_wh = cls.energy_for_tariff(
            today_points,
            "HC",
        )

        cost_peak_today = (energy_peak_today_wh / 1000) * peak_price
        cost_off_peak_today = (energy_off_peak_today_wh / 1000) * off_peak_price
        cost_today = cost_peak_today + cost_off_peak_today

        energy_week_wh = cls.total_energy(week_points)
        energy_month_wh = cls.total_energy(month_points)
        energy_year_wh = cls.total_energy(year_points)

        cost_week = cls.calculate_cost(
            week_points,
            peak_price=peak_price,
            off_peak_price=off_peak_price,
        )

        cost_month = cls.calculate_cost(
            month_points,
            peak_price=peak_price,
            off_peak_price=off_peak_price,
        )

        cost_year = cls.calculate_cost(
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
    def total_energy(
        points: list[EnergyPoint],
    ) -> float:
        """Return total energy in Wh."""
        return sum(point.energy for point in points)

    @staticmethod
    def energy_for_tariff(
        points: list[EnergyPoint],
        tariff: str,
    ) -> float:
        """Return energy in Wh for a tariff."""
        return sum(point.energy for point in points if point.tariff == tariff)

    @classmethod
    def calculate_cost(
        cls,
        points: list[EnergyPoint],
        *,
        peak_price: float,
        off_peak_price: float,
    ) -> float:
        """Calculate total cost from HP and HC energy."""
        peak_energy_wh = cls.energy_for_tariff(
            points,
            "HP",
        )

        off_peak_energy_wh = cls.energy_for_tariff(
            points,
            "HC",
        )

        return (peak_energy_wh / 1000) * peak_price + (
            off_peak_energy_wh / 1000
        ) * off_peak_price

    @classmethod
    def build_projections(
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
        ) = cls.project_month(
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
    def points_since(
        points: list[EnergyPoint],
        start: datetime,
    ) -> list[EnergyPoint]:
        """Return points at or after a local datetime."""
        return [point for point in points if dt_util.as_local(point.timestamp) >= start]

    @staticmethod
    def project_month(
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

    @staticmethod
    def find_total_module(
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
