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
ENERGY_INDEX = 0
ENERGY_INDEXES = (1, 2, 3)
PRICE_INDEXES = (4, 5, 6)


def decode_energy_points(
    data: dict[str, Any],
) -> list[EnergyPoint]:
    """Decode the first module from a gethomemeasure response."""
    points_by_module = decode_energy_points_by_module(data)

    if not points_by_module:
        return []

    return next(iter(points_by_module.values()))


def decode_energy_points_by_module(
    data: dict[str, Any],
) -> dict[str, list[EnergyPoint]]:
    """Decode a gethomemeasure response grouped by module ID."""
    modules = _extract_modules(data)

    if modules is None:
        return {}

    result: dict[str, list[EnergyPoint]] = {}

    for module in modules:
        if not isinstance(module, dict):
            continue

        module_id = module.get("id")
        measures = module.get("measures")

        if not isinstance(module_id, str) or not isinstance(measures, list):
            continue

        points = _decode_measures(measures)
        points.sort(key=lambda point: point.timestamp)
        result[module_id] = points

    return result


def _extract_modules(
    data: dict[str, Any],
) -> list[object] | None:
    """Extract modules from a private measurement response."""
    body = data.get("body")
    if not isinstance(body, dict):
        return None

    home = body.get("home")
    if not isinstance(home, dict):
        return None

    modules = home.get("modules")
    if not isinstance(modules, list):
        return None

    return modules


def _decode_measures(
    measures: list[object],
) -> list[EnergyPoint]:
    """Decode all measurement blocks for one module."""
    points: list[EnergyPoint] = []

    for measure in measures:
        if not isinstance(measure, dict):
            continue

        beg_time = measure.get("beg_time")
        step_time = measure.get("step_time")
        values = measure.get("value")

        if (
            not isinstance(beg_time, int)
            or isinstance(beg_time, bool)
            or not isinstance(step_time, int)
            or isinstance(step_time, bool)
            or not isinstance(values, list)
        ):
            continue

        for index, row in enumerate(values):
            if not isinstance(row, list):
                continue

            energy = _number_at(row, ENERGY_INDEX)

            if energy is None:
                energy = _sum_numbers(row, ENERGY_INDEXES)

            if energy is None:
                continue

            points.append(
                EnergyPoint(
                    timestamp=datetime.fromtimestamp(
                        beg_time + index * step_time,
                        UTC,
                    ),
                    energy=energy,
                    price=_sum_numbers(row, PRICE_INDEXES),
                )
            )

    return points


def _sum_numbers(
    row: list[object],
    indexes: tuple[int, ...],
) -> float | None:
    """Sum all numeric values at the requested indexes."""
    values = [
        float(row[index])
        for index in indexes
        if index < len(row) and _is_number(row[index])
    ]

    return sum(values) if values else None


def _number_at(
    row: list[object],
    index: int,
) -> float | None:
    """Return a numeric value at the requested index."""
    if index >= len(row):
        return None

    value = row[index]

    return float(value) if _is_number(value) else None


def _is_number(value: object) -> bool:
    """Return whether a value is numeric but not boolean."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)
