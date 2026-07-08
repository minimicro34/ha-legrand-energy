"""Models for energy contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class LegrandContractZone:
    """Contract zone."""

    id: int
    price: float
    price_type: str


@dataclass(slots=True)
class LegrandContractTimetableEntry:
    """Contract timetable entry."""

    zone_id: int
    m_offset: int


@dataclass(slots=True)
class LegrandContract:
    """Electricity contract."""

    id: str
    type: str
    tariff: str
    tariff_option: str
    power_threshold: float
    power_unit: str
    peak_price: float | None = None
    off_peak_price: float | None = None
    zones: list[LegrandContractZone] | None = None
    timetable: list[LegrandContractTimetableEntry] | None = None