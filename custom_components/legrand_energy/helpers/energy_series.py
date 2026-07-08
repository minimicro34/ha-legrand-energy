"""Energy time series helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class EnergyPoint:
    """One energy sample."""

    timestamp: datetime
    energy: float
    price: float | None = None