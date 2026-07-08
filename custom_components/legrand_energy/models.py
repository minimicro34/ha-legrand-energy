"""Models for Legrand Energy."""

from __future__ import annotations

from dataclasses import dataclass

from .helpers.module_statistics import ModuleStatistics


@dataclass(slots=True)
class LegrandModule:
    """Legrand module."""

    id: str
    name: str
    type: str
    bridge: str | None = None
    room: str | None = None
    setup_date: int | None = None

    energy_tariff1: float | None = None
    energy_tariff2: float | None = None
    price_tariff1: float | None = None
    price_tariff2: float | None = None
    last_measure: int | None = None

    statistics: ModuleStatistics | None = None