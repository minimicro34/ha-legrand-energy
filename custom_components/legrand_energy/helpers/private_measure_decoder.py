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
    result: dict[str, list[EnergyPoint]] = {}

    body = data.get("body")
    if not isinstance(body, dict):
        return result

    home = body.get("home")
    if not isinstance(home, dict):
        return result

    modules = home.get("modules")
    if not isinstance(modules, list):
        return result

    for module in modules:
        if not isinstance(module, dict):
            continue

        module_id = module.get("id")
        if not isinstance(module_id, str):
            continue

        points: list[EnergyPoint] = []

        measures = module.get("measures", [])
        if not isinstance(measures, list):
            continue

        for measure in measures:
            if not isinstance(measure, dict):
                continue

            beg_time = measure.get("beg_time")
            step_time = measure.get("step_time")

            if not isinstance(beg_time, int):
                continue

            if not isinstance(step_time, int):
                continue

            values = measure.get("value", [])
            if not isinstance(values, list):
                continue

            for index, row in enumerate(values):
                if not isinstance(row, list):
                    continue

                energy = _first_number(
                    row,
                    ENERGY_INDEXES,
                )
                if energy is None:
                    continue

                price = _first_number(
                    row,
                    PRICE_INDEXES,
                )

                points.append(
                    EnergyPoint(
                        timestamp=datetime.fromtimestamp(
                            beg_time + index * step_time,
                            UTC,
                        ),
                        energy=float(energy),
                        price=(float(price) if price is not None else None),
                    )
                )

        result[module_id] = sorted(
            points,
            key=lambda point: point.timestamp,
        )

    return result


def _first_number(
    row: list[Any],
    indexes: tuple[int, ...],
) -> float | int | None:
    """Return the first numeric value from the requested indexes."""
    for index in indexes:
        if index >= len(row):
            continue

        value = row[index]

        if isinstance(value, int | float):
            return value

    return None
