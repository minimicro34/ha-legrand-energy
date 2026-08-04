"""Decode private gethomemeasure responses."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..models import FluidType
from .energy_series import EnergyPoint

# Format électrique compact :
# 0 sum_energy_elec
# 1 sum_energy_elec$0
# 2 sum_energy_elec$1
# 3 sum_energy_elec$2
# 4 sum_energy_price$0
# 5 sum_energy_price$1
# 6 sum_energy_price$2
ELECTRICITY_ENERGY_INDEXES = (1, 2, 3)
ELECTRICITY_PRICE_INDEXES = (4, 5, 6)

# Format eau/gaz :
# 0 sum_fluid_consumption$0
# 1 sum_fluid_price$0
FLUID_CONSUMPTION_INDEX = 0
FLUID_PRICE_INDEX = 1


def decode_energy_points(
    data: dict[str, Any],
) -> list[EnergyPoint]:
    """Decode the first electricity module from a response."""
    points_by_module = decode_energy_points_by_module(data)

    if not points_by_module:
        return []

    return next(iter(points_by_module.values()))


def decode_energy_points_by_module(
    data: dict[str, Any],
) -> dict[str, list[EnergyPoint]]:
    """Decode an electricity response grouped by module ID."""
    return decode_points_by_module(
        data,
        fluid_type=FluidType.ELECTRICITY,
    )


def decode_points_by_module(
    data: dict[str, Any],
    *,
    fluid_type: FluidType,
) -> dict[str, list[EnergyPoint]]:
    """Decode a private measurement response grouped by module ID."""
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

        measures = module.get("measures")
        if not isinstance(measures, list):
            continue

        points: list[EnergyPoint] = []

        for measure in measures:
            if not isinstance(measure, dict):
                continue

            beg_time = measure.get("beg_time")
            step_time = measure.get("step_time")
            values = measure.get("value")

            if not isinstance(beg_time, int):
                continue

            if not isinstance(step_time, int):
                continue

            if not isinstance(values, list):
                continue

            for index, row in enumerate(values):
                if not isinstance(row, list):
                    continue

                decoded = _decode_row(
                    row,
                    fluid_type=fluid_type,
                )

                if decoded is None:
                    continue

                consumption, price = decoded

                points.append(
                    EnergyPoint(
                        timestamp=datetime.fromtimestamp(
                            beg_time + index * step_time,
                            UTC,
                        ),
                        energy=consumption,
                        price=price,
                    )
                )

        result[module_id] = sorted(
            points,
            key=lambda point: point.timestamp,
        )

    return result


def _decode_row(
    row: list[object],
    *,
    fluid_type: FluidType,
) -> tuple[float, float | None] | None:
    """Decode one measurement row for the requested fluid type."""
    if fluid_type is FluidType.ELECTRICITY:
        energy = _number_at(row, 0)

        if energy is None:
            energy = _sum_numbers(
                row,
                ELECTRICITY_ENERGY_INDEXES,
            )

        if energy is None:
            return None

        price = _sum_numbers(
            row,
            ELECTRICITY_PRICE_INDEXES,
        )

        return energy, price

    consumption = _number_at(
        row,
        FLUID_CONSUMPTION_INDEX,
    )

    if consumption is None:
        return None

    price = _number_at(
        row,
        FLUID_PRICE_INDEX,
    )

    return consumption, price


def _sum_numbers(
    row: list[object],
    indexes: tuple[int, ...],
) -> float | None:
    """Sum all numeric values at the requested indexes."""
    total = 0.0
    found = False

    for index in indexes:
        if index >= len(row):
            continue

        value = row[index]

        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue

        total += float(value)
        found = True

    return total if found else None


def _number_at(
    row: list[object],
    index: int,
) -> float | None:
    """Return a numeric value at the requested index."""
    if index >= len(row):
        return None

    value = row[index]

    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None

    return float(value)
