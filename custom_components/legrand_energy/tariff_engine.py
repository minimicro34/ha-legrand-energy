"""Electricity tariff engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .contract_models import Contract


MINUTES_PER_WEEK = 7 * 24 * 60


@dataclass(slots=True)
class TariffState:
    """Current tariff state."""

    zone_id: int
    zone_name: str
    price: float
    next_change: datetime


class TariffEngine:
    """Electricity tariff engine."""

    def __init__(self, contract: Contract) -> None:
        """Initialize engine."""
        self._contract = contract
        self._timetable = sorted(
            contract.timetable,
            key=lambda period: period.minute_offset,
        )

    def state_at(self, when: datetime) -> TariffState:
        """Return tariff state at given datetime."""
        minute = when.weekday() * 1440 + when.hour * 60 + when.minute

        current = self._timetable[-1]

        for period in self._timetable:
            if minute >= period.minute_offset:
                current = period
            else:
                break

        zone = next(
            zone for zone in self._contract.zones if zone.id == current.zone_id
        )

        next_period = self._timetable[0]

        for period in self._timetable:
            if period.minute_offset > minute:
                next_period = period
                break

        delta = next_period.minute_offset - minute

        if delta <= 0:
            delta += MINUTES_PER_WEEK

        return TariffState(
            zone_id=zone.id,
            zone_name=zone.price_type,
            price=zone.price,
            next_change=when + timedelta(minutes=delta),
        )

    def current_state(self, when: datetime | None = None) -> TariffState:
        """Return current tariff state."""
        if when is None:
            when = datetime.now()

        return self.state_at(when)

    def current_price(self, when: datetime | None = None) -> float:
        """Return current price."""
        return self.current_state(when).price

    def current_zone(self, when: datetime | None = None) -> str:
        """Return current tariff zone."""
        return self.current_state(when).zone_name

    def is_off_peak(self, when: datetime | None = None) -> bool:
        """Return True if off peak."""
        return self.current_zone(when) == "off_peak"

    def is_peak(self, when: datetime | None = None) -> bool:
        """Return True if peak."""
        return self.current_zone(when) == "peak"

    def next_change(self, when: datetime | None = None) -> datetime:
        """Return next tariff change."""
        return self.current_state(when).next_change