from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class MeasurePoint:
    """One point returned by gethomemeasure."""

    timestamp: int
    values: dict[str, float]


@dataclass(slots=True)
class ModuleMeasurement:
    """One Legrand circuit."""

    id: str
    name: str
    type: str
    bridge: str | None = None

    history: list[MeasurePoint] = field(default_factory=list)

    raw: dict = field(default_factory=dict)

    @property
    def latest(self) -> MeasurePoint | None:
        if not self.history:
            return None
        return self.history[-1]

    def get(self, key: str) -> float:
        latest = self.latest

        if latest is None:
            return 0.0

        return float(latest.values.get(key, 0))

    @property
    def energy(self) -> float:
        latest = self.latest

        if latest is None:
            return 0.0

        return sum(
            value
            for name, value in latest.values.items()
            if name.startswith("sum_energy_elec")
        )

    @property
    def price(self) -> float:
        latest = self.latest

        if latest is None:
            return 0.0

        return sum(
            value
            for name, value in latest.values.items()
            if name.startswith("sum_energy_price")
        )