"""Module statistics."""

from __future__ import annotations

from dataclasses import dataclass

from .daily_statistics import DailyStatistics
from .energy_series import EnergyPoint
from .monthly_projection import MonthlyProjection
from .projections import DailyProjection


@dataclass(slots=True)
class ModuleStatistics:
    """Statistics for one electrical circuit."""

    points: list[EnergyPoint]

    total_energy: float
    total_cost: float
    dashboard_total: float

    daily: DailyStatistics | None = None
    projection: DailyProjection | None = None
    monthly_projection: MonthlyProjection | None = None
