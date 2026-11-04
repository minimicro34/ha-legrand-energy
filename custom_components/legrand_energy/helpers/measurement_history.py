"""Pure helpers for exposing cached Netatmo energy intervals to a chart.

The source API reports energy in Wh, not kWh. Never infer the interval
duration from the requested API scale: use each decoded point's actual step.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .energy_series import EnergyPoint


def serialize_energy_history(
    points: list[EnergyPoint],
    *,
    start: datetime,
    end: datetime,
    limit: int = 3000,
) -> list[dict[str, Any]]:
    """Return bounded, ordered intervals, without fabricating missing data.

    Timestamps are the raw decoded point timestamps. Consumers must not
    assume they represent interval ends or that intervals are contiguous.
    """
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("History boundaries must be timezone-aware")
    if end <= start:
        raise ValueError("History end must be after start")
    if not 1 <= limit <= 3000:
        raise ValueError("History limit must be between 1 and 3000")

    selected = sorted(
        (
            point
            for point in points
            if start <= point.timestamp < end
            and point.interval_seconds is not None
            and point.interval_seconds > 0
            and point.energy >= 0
        ),
        key=lambda point: point.timestamp,
    )
    if len(selected) > limit:
        raise ValueError("History exceeds maximum interval count")

    return [
        {
            "timestamp": point.timestamp.isoformat(),
            "energy_kwh": point.energy / 1000,
            "interval_seconds": point.interval_seconds,
            "peak_kwh": (
                point.peak_energy / 1000 if point.peak_energy is not None else None
            ),
            "off_peak_kwh": (
                point.off_peak_energy / 1000
                if point.off_peak_energy is not None
                else None
            ),
            "tariff": (
                point.tariff
                if point.interval_seconds is not None
                and point.interval_seconds < 23 * 3600
                else None
            ),
        }
        for point in selected
    ]
