"""Energy accumulator."""

from __future__ import annotations

from .energy_series import EnergyPoint


class EnergyAccumulator:
    """Accumulate energy samples."""

    def __init__(self) -> None:
        self._total = 0.0

    @property
    def total(self) -> float:
        return self._total

    def reset(self) -> None:
        """Reset accumulator."""
        self._total = 0.0

    def add(self, point: EnergyPoint) -> float:
        """Add one sample and return cumulative energy."""
        self._total += point.energy
        return self._total