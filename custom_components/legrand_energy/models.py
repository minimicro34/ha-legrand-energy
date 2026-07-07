from dataclasses import dataclass


@dataclass(slots=True)
class LegrandModule:
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

    @property
    def is_bridge(self) -> bool:
        """Return True if this module is the EcoMeter bridge."""
        return self.bridge is None