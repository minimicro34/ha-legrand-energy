"""Data models for Legrand Energy."""

from __future__ import annotations

from dataclasses import dataclass, field

from .contract_models import Contract
from .tariff_engine import TariffState


@dataclass(frozen=True, slots=True)
class LegrandModule:
    """Represent a Legrand Energy module."""

    id: str
    name: str
    type: str
    bridge: str | None = None
    room: str | None = None
    setup_date: int | None = None


@dataclass(frozen=True, slots=True)
class LegrandMeasurements:
    """Represent calculated energy measurements."""

    power: float | None = None

    energy_today: float | None = None
    energy_week: float | None = None
    energy_month: float | None = None
    energy_year: float | None = None

    cost_today: float | None = None
    cost_peak_today: float | None = None
    cost_off_peak_today: float | None = None

    cost_week: float | None = None
    cost_month: float | None = None
    cost_year: float | None = None


@dataclass(frozen=True, slots=True)
class LegrandProjections:
    """Represent projected energy values."""

    energy_end_of_day: float | None = None
    energy_end_of_month: float | None = None
    cost_end_of_day: float | None = None
    cost_end_of_month: float | None = None


@dataclass(frozen=True, slots=True)
class LegrandEnergyData:
    """Represent all data exposed by the coordinator."""

    modules: dict[str, LegrandModule]
    contract: Contract | None = None
    tariff: TariffState | None = None
    measurements: LegrandMeasurements | None = None
    measurements_by_module: dict[str, LegrandMeasurements] = field(default_factory=dict)
    projections: LegrandProjections | None = None
