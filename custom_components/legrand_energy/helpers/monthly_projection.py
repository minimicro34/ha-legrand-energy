"""Monthly projection helpers."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class MonthlyProjection:
    """Monthly projection."""

    projected_energy: float
    projected_cost: float
    elapsed_ratio: float


def project_month(
    energy: float,
    cost: float,
    now: datetime,
) -> MonthlyProjection:
    """Project a month using the estimated full-day values."""
    days_in_month = monthrange(now.year, now.month)[1]

    return MonthlyProjection(
        projected_energy=energy * days_in_month,
        projected_cost=cost * days_in_month,
        elapsed_ratio=1.0 / days_in_month,
    )
