"""Fluid measurement models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FluidMeasurements:
    """Represent calculated fluid measurements."""

    consumption_today: float | None = None
    consumption_week: float | None = None
    consumption_month: float | None = None
    consumption_year: float | None = None

    cost_today: float | None = None
    cost_week: float | None = None
    cost_month: float | None = None
    cost_year: float | None = None
