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
    peak_price: float,
    off_peak_price: float,
) -> DailyStatistics:
    """Compute daily statistics."""
    stats = DailyStatistics(points=len(points))

    for point in points:
        energy_kwh = point.energy / 1000

        stats.total_energy += point.energy

        if point.tariff == "peak":
            cost = energy_kwh * peak_price
            stats.peak_energy += point.energy
            stats.peak_cost += cost

        elif point.tariff == "off_peak":
            cost = energy_kwh * off_peak_price
            stats.off_peak_energy += point.energy
            stats.off_peak_cost += cost

        else:
            cost = 0.0

        stats.total_cost += cost

    return stats
