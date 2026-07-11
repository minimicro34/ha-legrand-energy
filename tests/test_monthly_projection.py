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
    """Project a month from estimated full-day values."""

    days = monthrange(now.year, now.month)[1]

    return MonthlyProjection(
        projected_energy=energy * days,
        projected_cost=cost * days,
        elapsed_ratio=1.0 / days,
    )
