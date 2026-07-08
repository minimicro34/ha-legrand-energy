"""Monthly projection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from calendar import monthrange


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
    """Project end-of-month energy and cost."""

    days_in_month = monthrange(now.year, now.month)[1]

    elapsed_days = (
        now.day - 1
        + (now.hour * 60 + now.minute) / (24 * 60)
    )

    if elapsed_days <= 0:
        return MonthlyProjection(
            projected_energy=0.0,
            projected_cost=0.0,
            elapsed_ratio=0.0,
        )

    elapsed_ratio = elapsed_days / days_in_month

    return MonthlyProjection(
        projected_energy=energy / elapsed_ratio,
        projected_cost=cost / elapsed_ratio,
        elapsed_ratio=elapsed_ratio,
    )