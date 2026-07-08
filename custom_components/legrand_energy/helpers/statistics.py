"""Statistics helpers."""

from __future__ import annotations

from collections.abc import Iterable

from .energy_series import EnergyPoint


def total_energy(points: Iterable[EnergyPoint]) -> float:
    """Return total energy."""
    return sum(point.energy for point in points)


def total_cost(points: Iterable[EnergyPoint]) -> float:
    """Return total cost."""
    return sum(point.price or 0 for point in points)