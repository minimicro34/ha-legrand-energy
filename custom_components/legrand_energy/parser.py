"""Parser for Legrand Energy private API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class EnergyMeasure:
    """Parsed electricity measure."""

    energy_tariff1: float | None = None
    energy_tariff2: float | None = None
    price_tariff1: float | None = None
    price_tariff2: float | None = None
    timestamp: int | None = None


def parse_energy_measure(data: dict[str, Any]) -> EnergyMeasure:
    """Parse gethomemeasure response."""

    modules = data.get("body", {}).get("home", {}).get("modules", [])

    if not modules:
        return EnergyMeasure()

    measures = modules[0].get("measures", [])

    if not measures:
        return EnergyMeasure()

    latest_time = 0
    latest_values: list[Any] | None = None

    for measure in measures:
        beg = measure.get("beg_time", 0)
        step = measure.get("step_time", 0)

        for index, values in enumerate(measure.get("value", [])):
            ts = beg + index * step

            if ts > latest_time:
                latest_time = ts
                latest_values = values

    if latest_values is None:
        return EnergyMeasure()

    return EnergyMeasure(
        energy_tariff1=latest_values[2],
        energy_tariff2=latest_values[3],
        price_tariff1=latest_values[5],
        price_tariff2=latest_values[6],
        timestamp=latest_time,
    )
