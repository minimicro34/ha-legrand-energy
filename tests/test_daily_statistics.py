from datetime import UTC, datetime

from custom_components.legrand_energy.helpers.daily_statistics import (
    compute_daily_statistics,
)
from custom_components.legrand_energy.helpers.energy_series import EnergyPoint


def test_daily_statistics() -> None:
    points = [
        EnergyPoint(
            timestamp=datetime(2026, 7, 8, 10, tzinfo=UTC),
            energy=100,
            price=0.02,
            tariff="peak",
        ),
        EnergyPoint(
            timestamp=datetime(2026, 7, 8, 23, tzinfo=UTC),
            energy=200,
            price=0.01,
            tariff="off_peak",
        ),
    ]

    stats = compute_daily_statistics(points)

    assert stats.points == 2
    assert stats.total_energy == 300
    assert stats.total_cost == 0.03

    assert stats.peak_energy == 100
    assert stats.off_peak_energy == 200

    assert stats.peak_cost == 0.02
    assert stats.off_peak_cost == 0.01