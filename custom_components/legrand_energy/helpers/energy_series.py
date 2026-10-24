"""Energy time series helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class EnergyPoint:
    """Energy measurement."""

    timestamp: datetime
    energy: float
    price: float | None = None
    interval_seconds: int | None = None

    tariff: str | None = None
    zone_id: int | None = None
