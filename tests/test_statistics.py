"""Tests for statistics helpers."""

from datetime import UTC, datetime

from custom_components.legrand_energy.helpers.energy_series import EnergyPoint
from custom_components.legrand_energy.helpers.statistics import total_cost, total_energy


def test_statistics_totals() -> None:
    """Test statistics totals."""
    points = [
        EnergyPoint(datetime(2026, 7, 7, 10, 0, tzinfo=UTC), 100, 0.02),
        EnergyPoint(datetime(2026, 7, 7, 10, 30, tzinfo=UTC), 200, 0.04),
    ]

    assert total_energy(points) == 300
    assert total_cost(points) == 0.06