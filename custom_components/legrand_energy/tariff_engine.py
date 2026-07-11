"""Electricity tariff engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .contract_models import Contract

MINUTES_PER_DAY = 24 * 60
MINUTES_PER_WEEK = 7 * MINUTES_PER_DAY


@dataclass(frozen=True, slots=True)
class TariffState:
    """Current tariff state."""

    zone_id: int
    zone_name: str
    price: float | None
    next_change: datetime | None

    @property
    def price_type(self) -> str:
        """Return the current tariff name."""
        return self.zone_name

    @property
    def is_off_peak(self) -> bool:
        """Return whether the current tariff is off-peak."""
        value = self.zone_name.casefold().replace("-", "_").replace(" ", "_")

        return value in {
            "hc",
            "heures_creuses",
            "off_peak",
        }


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
        """Return tariff state at a given datetime."""
        when = self._as_local_aware(when)

        if not self._timetable:
            raise ValueError("Contract timetable is empty")

        minute = when.weekday() * MINUTES_PER_DAY + when.hour * 60 + when.minute

        current_period = self._timetable[-1]

        for period in self._timetable:
            if period.minute_offset <= minute:
                current_period = period
            else:
                break

        zone = next(
            (
                zone
                for zone in self._contract.zones
                if zone.id == current_period.zone_id
            ),
            None,
        )

        if zone is None:
            raise ValueError(f"Unknown tariff zone: {current_period.zone_id}")

        next_period = next(
            (period for period in self._timetable if period.minute_offset > minute),
            self._timetable[0],
        )

        week_start = (when - timedelta(days=when.weekday())).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        next_change = week_start + timedelta(minutes=next_period.minute_offset)

        if next_change <= when:
            next_change += timedelta(weeks=1)

        return TariffState(
            zone_id=zone.id,
            zone_name=zone.price_type,
            price=zone.price,
            next_change=next_change,
        )

    def current_state(
        self,
        when: datetime | None = None,
    ) -> TariffState:
        """Return current tariff state."""
        return self.state_at(datetime.now().astimezone() if when is None else when)

    def current_price(
        self,
        when: datetime | None = None,
    ) -> float | None:
        """Return current price."""
        return self.current_state(when).price

    def current_zone(
        self,
        when: datetime | None = None,
    ) -> str:
        """Return current tariff zone."""
        return self.current_state(when).zone_name

    def is_off_peak(
        self,
        when: datetime | None = None,
    ) -> bool:
        """Return True if the current period is off peak."""
        return self.current_state(when).is_off_peak

    def is_peak(
        self,
        when: datetime | None = None,
    ) -> bool:
        """Return True if the current period is peak."""
        return not self.current_state(when).is_off_peak

    def next_change(
        self,
        when: datetime | None = None,
    ) -> datetime | None:
        """Return the next tariff change."""
        return self.current_state(when).next_change

    @staticmethod
    def _as_local_aware(when: datetime) -> datetime:
        """Return a timezone-aware local datetime."""
        if when.tzinfo is None:
            return when.astimezone()

        return when.astimezone()
