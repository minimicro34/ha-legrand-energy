"""Tariff schedule helpers for Legrand Energy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.util import dt as dt_util

from .contract_models import LegrandContract, LegrandContractTimetableEntry


MINUTES_PER_WEEK = 7 * 24 * 60


@dataclass(slots=True)
class TariffState:
    """Current tariff state."""

    price_type: str | None
    price: float | None
    next_change: datetime | None
    remaining: timedelta | None


class TariffSchedule:
    """Compute current tariff from contract timetable."""

    def __init__(self, contract: LegrandContract) -> None:
        """Initialize schedule."""
        self.contract = contract

    def current(self, now: datetime | None = None) -> TariffState:
        """Return current tariff state."""
        if now is None:
            now = dt_util.now()

        zones = {zone.id: zone for zone in self.contract.zones or []}
        timetable = sorted(
            self.contract.timetable or [],
            key=lambda item: item.m_offset,
        )

        if not zones or not timetable:
            return TariffState(None, None, None, None)

        minute = self._minute_of_week(now)
        current_entry = self._current_entry(timetable, minute)
        next_entry = self._next_entry(timetable, minute)

        zone = zones.get(current_entry.zone_id)
        next_change = self._next_change_datetime(now, next_entry.m_offset)

        return TariffState(
            price_type=zone.price_type if zone else None,
            price=zone.price if zone else None,
            next_change=next_change,
            remaining=next_change - now if next_change else None,
        )

    @staticmethod
    def _minute_of_week(now: datetime) -> int:
        """Return minute offset from Monday 00:00."""
        return now.weekday() * 1440 + now.hour * 60 + now.minute

    @staticmethod
    def _current_entry(
        timetable: list[LegrandContractTimetableEntry],
        minute: int,
    ) -> LegrandContractTimetableEntry:
        """Return current timetable entry."""
        current = timetable[-1]
        for entry in timetable:
            if entry.m_offset <= minute:
                current = entry
            else:
                break
        return current

    @staticmethod
    def _next_entry(
        timetable: list[LegrandContractTimetableEntry],
        minute: int,
    ) -> LegrandContractTimetableEntry:
        """Return next timetable entry."""
        for entry in timetable:
            if entry.m_offset > minute:
                return entry
        return timetable[0]

    @staticmethod
    def _next_change_datetime(now: datetime, next_offset: int) -> datetime:
        """Return next change datetime."""
        week_start = (now - timedelta(days=now.weekday())).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        next_change = week_start + timedelta(minutes=next_offset)

        if next_change <= now:
            next_change += timedelta(days=7)

        return next_change   