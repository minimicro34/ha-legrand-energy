"""Daily statistics engine."""

from __future__ import annotations

from dataclasses import dataclass

from .energy_series import EnergyPoint


@dataclass(slots=True)
class DailyStatistics:
    """Daily statistics."""

    total_energy: float = 0.0
    total_cost: float = 0.0

    peak_energy: float = 0.0
    off_peak_energy: float = 0.0

    peak_cost: float = 0.0
    off_peak_cost: float = 0.0

    points: int = 0


def compute_daily_statistics(
    points: list[EnergyPoint],
) -> DailyStatistics:
    """Compute daily statistics."""

    stats = DailyStatistics(points=len(points))

    for point in points:
        price = point.price or 0.0

        stats.total_energy += point.energy
        stats.total_cost += price

        if point.tariff == "peak":
            stats.peak_energy += point.energy
            stats.peak_cost += price

        elif point.tariff == "off_peak":
            stats.off_peak_energy += point.energy
            stats.off_peak_cost += price

    return stats