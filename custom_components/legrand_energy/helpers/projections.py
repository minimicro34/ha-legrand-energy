"""Projection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class DailyProjection:
    """Daily projection."""

    projected_energy: float
    projected_cost: float
    elapsed_ratio: float


def project_today(
    energy: float,
    cost: float,
    now: datetime,
) -> DailyProjection:
    """Project end-of-day energy and cost."""
    minutes_elapsed = now.hour * 60 + now.minute

    if minutes_elapsed <= 0:
        return DailyProjection(
            projected_energy=0.0,
            projected_cost=0.0,
            elapsed_ratio=0.0,
        )

    total_minutes = 24 * 60
    elapsed_ratio = minutes_elapsed / total_minutes

    return DailyProjection(
        projected_energy=energy / elapsed_ratio,
        projected_cost=cost / elapsed_ratio,
        elapsed_ratio=elapsed_ratio,
    )
