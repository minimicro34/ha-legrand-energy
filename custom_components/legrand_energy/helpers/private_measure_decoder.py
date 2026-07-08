"""Decode private gethomemeasure responses."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .energy_series import EnergyPoint


# Format court utilisé actuellement :
# 0 sum_energy_elec
# 1 sum_energy_elec$0
# 2 sum_energy_elec$1
# 3 sum_energy_elec$2
# 4 sum_energy_price$0
# 5 sum_energy_price$1
# 6 sum_energy_price$2
ENERGY_INDEXES = (1, 2, 3)
PRICE_INDEXES = (4, 5, 6)


def decode_energy_points(data: dict[str, Any]) -> list[EnergyPoint]:
    """Decode gethomemeasure response into energy points."""
    points: list[EnergyPoint] = []

    modules = data.get("body", {}).get("home", {}).get("modules", [])
    if not modules:
        return points

    for measure in modules[0].get("measures", []):
        beg_time = measure.get("beg_time")
        step_time = measure.get("step_time")

        if beg_time is None or step_time is None:
            continue

        for index, row in enumerate(measure.get("value", [])):
            if not isinstance(row, list):
                continue

            energy = _first_number(row, ENERGY_INDEXES)
            if energy is None:
                continue

            price = _first_number(row, PRICE_INDEXES)

            points.append(
                EnergyPoint(
                    timestamp=datetime.fromtimestamp(
                        beg_time + index * step_time,
                        UTC,
                    ),
                    energy=float(energy),
                    price=float(price) if price is not None else None,
                )
            )

    return sorted(points, key=lambda point: point.timestamp)


def _first_number(row: list[Any], indexes: tuple[int, ...]) -> float | int | None:
    """Return first numeric value from row at indexes."""
    for index in indexes:
        if index >= len(row):
            continue

        value = row[index]

        if isinstance(value, int | float):
            return value

    return None