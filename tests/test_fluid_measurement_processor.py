"""Tests for fluid measurement processing helpers."""

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.legrand_energy.helpers.energy_series import EnergyPoint
from custom_components.legrand_energy.helpers.fluid_measurement_processor import (
    FluidMeasurementProcessor,
)


def _point(
    timestamp: datetime,
    consumption: float,
    price: float | None,
) -> EnergyPoint:
    """Build one fluid measurement point."""
    return EnergyPoint(
        timestamp=timestamp,
        energy=consumption,
        price=price,
    )


def test_points_since() -> None:
    """Filter points from the requested start time."""
    start = datetime(2026, 8, 4, 12, tzinfo=UTC)

    points = [
        _point(start - timedelta(minutes=5), 10.0, 0.1),
        _point(start, 20.0, 0.2),
        _point(start + timedelta(minutes=5), 30.0, 0.3),
    ]

    filtered = FluidMeasurementProcessor.points_since(points, start)

    assert [point.energy for point in filtered] == [20.0, 30.0]


def test_build_measurements() -> None:
    """Build consumption and cost totals."""
    now = datetime(2026, 8, 4, 12, tzinfo=UTC)

    today_points = [
        _point(now, 100.0, 0.4),
        _point(now + timedelta(minutes=5), 25.0, 0.1),
    ]
    week_points = [
        _point(now - timedelta(days=1), 300.0, 0.9),
        *today_points,
    ]
    month_points = [
        _point(now - timedelta(days=10), 500.0, 1.5),
        *week_points,
    ]
    year_points = [
        _point(now - timedelta(days=100), 1_000.0, 3.0),
        *month_points,
    ]

    measurements = FluidMeasurementProcessor.build_measurements(
        today_points=today_points,
        week_points=week_points,
        month_points=month_points,
        year_points=year_points,
    )

    assert measurements.consumption_today == 125.0
    assert measurements.consumption_week == 425.0
    assert measurements.consumption_month == 925.0
    assert measurements.consumption_year == 1_925.0

    assert measurements.cost_today == pytest.approx(0.5)
    assert measurements.cost_week == pytest.approx(1.4)
    assert measurements.cost_month == pytest.approx(2.9)
    assert measurements.cost_year == pytest.approx(5.9)


def test_missing_costs_return_zero() -> None:
    """Return zero cost when no point contains a price."""
    now = datetime(2026, 8, 4, 12, tzinfo=UTC)
    points = [_point(now, 100.0, None)]

    measurements = FluidMeasurementProcessor.build_measurements(
        today_points=points,
        week_points=points,
        month_points=points,
        year_points=points,
    )

    assert measurements.consumption_today == 100.0
    assert measurements.consumption_week == 100.0
    assert measurements.consumption_month == 100.0
    assert measurements.consumption_year == 100.0

    assert measurements.cost_today == 0.0
    assert measurements.cost_week == 0.0
    assert measurements.cost_month == 0.0
    assert measurements.cost_year == 0.0


def test_empty_points_return_zero_totals() -> None:
    """Return zero consumption and cost for an empty series."""
    measurements = FluidMeasurementProcessor.build_measurements(
        today_points=[],
        week_points=[],
        month_points=[],
        year_points=[],
    )

    assert measurements.consumption_today == 0.0
    assert measurements.consumption_week == 0.0
    assert measurements.consumption_month == 0.0
    assert measurements.consumption_year == 0.0

    assert measurements.cost_today == 0.0
    assert measurements.cost_week == 0.0
    assert measurements.cost_month == 0.0
    assert measurements.cost_year == 0.0


def test_ignores_missing_prices_when_other_prices_exist() -> None:
    """Sum available prices while ignoring missing price values."""
    now = datetime(2026, 8, 4, 12, tzinfo=UTC)

    points = [
        _point(now, 100.0, None),
        _point(now + timedelta(minutes=5), 25.0, 0.2),
        _point(now + timedelta(minutes=10), 10.0, None),
        _point(now + timedelta(minutes=15), 5.0, 0.1),
    ]

    measurements = FluidMeasurementProcessor.build_measurements(
        today_points=points,
        week_points=points,
        month_points=points,
        year_points=points,
    )

    assert measurements.consumption_today == 140.0
    assert measurements.cost_today == pytest.approx(0.3)
