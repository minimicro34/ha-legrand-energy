"""Tests for measurement processing projections."""

from datetime import UTC, datetime

import pytest

from custom_components.legrand_energy.helpers.measurement_processor import (
    MeasurementProcessor,
)


@pytest.mark.parametrize(
    ("now", "days_in_year"),
    [
        (datetime(2026, 7, 2, 12, tzinfo=UTC), 365),
        (datetime(2024, 7, 2, 12, tzinfo=UTC), 366),
    ],
)
def test_project_year(now: datetime, days_in_year: int) -> None:
    """Test annual projection for regular and leap years."""
    elapsed_days = now.timetuple().tm_yday - 0.5
    expected_factor = days_in_year / elapsed_days

    energy, cost = MeasurementProcessor.project_year(
        now=now,
        energy_year=1000.0,
        cost_year=200.0,
    )

    assert energy == pytest.approx(1000.0 * expected_factor)
    assert cost == pytest.approx(200.0 * expected_factor)


def test_project_year_at_start_of_year() -> None:
    """Do not project before any part of the year has elapsed."""
    energy, cost = MeasurementProcessor.project_year(
        now=datetime(2026, 1, 1, tzinfo=UTC),
        energy_year=0.0,
        cost_year=0.0,
    )

    assert energy is None
    assert cost is None


def test_calculate_cost_prefers_api_historical_prices() -> None:
    """Use Home Control's accumulated prices when they are available."""
    from custom_components.legrand_energy.helpers.energy_series import EnergyPoint

    points = [
        EnergyPoint(
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            energy=1000.0,
            price=0.18,
        ),
        EnergyPoint(
            timestamp=datetime(2026, 1, 2, tzinfo=UTC),
            energy=2000.0,
            price=0.36,
        ),
    ]

    assert MeasurementProcessor.calculate_cost(
        points,
        peak_price=99.0,
        off_peak_price=99.0,
    ) == pytest.approx(0.54)


@pytest.mark.parametrize(
    ("energy", "interval", "expected"),
    [
        (4.0, 1800, 8.0),
        (100.0, 1800, 200.0),
        (0.0, 300, 0.0),
        (1.0, 0, None),
        (1.0, -60, None),
        (1.0, None, None),
        (-1.0, 300, None),
        (float("nan"), 300, None),
        (float("inf"), 300, None),
    ],
)
def test_average_power_for_point(
    energy: float, interval: int | None, expected: float | None
) -> None:
    """Use actual API interval duration and reject invalid readings."""
    from custom_components.legrand_energy.helpers.energy_series import EnergyPoint

    point = EnergyPoint(
        timestamp=datetime(2026, 10, 24, tzinfo=UTC),
        energy=energy,
        interval_seconds=interval,
    )

    result = MeasurementProcessor.average_power_for_point(point)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected)
