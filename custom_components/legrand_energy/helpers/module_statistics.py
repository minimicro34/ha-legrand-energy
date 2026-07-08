"""Module statistics."""

from __future__ import annotations

from dataclasses import dataclass

from .energy_series import EnergyPoint


@dataclass(slots=True)
class ModuleStatistics:
    """Calculated statistics for one module."""

    points: list[EnergyPoint]
    total_energy: float
    total_cost: float
    dashboard_total: float