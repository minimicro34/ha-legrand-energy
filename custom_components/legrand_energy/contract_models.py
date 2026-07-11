"""Models for electricity contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TariffZone:
    """Tariff zone."""

    id: int
    price: float
    price_type: str


@dataclass(slots=True)
class TariffPeriod:
    """Tariff timetable entry."""

    zone_id: int
    minute_offset: int


@dataclass(slots=True)
class Contract:
    """Electricity contract."""

    id: str
    type: str
    tariff: str
    tariff_option: str

    power_threshold: int
    power_unit: str

    peak_price: float | None
    off_peak_price: float | None

    zones: list[TariffZone]
    timetable: list[TariffPeriod]
