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
