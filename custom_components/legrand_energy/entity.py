"""Base entity for Legrand Energy."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import LegrandEnergyCoordinator
from .models import LegrandModule


class LegrandEntity(CoordinatorEntity[LegrandEnergyCoordinator]):
    """Base Legrand entity."""

    def __init__(
        self,
        coordinator: LegrandEnergyCoordinator,
        module_id: str,
    ) -> None:
        """Initialize entity."""
        super().__init__(coordinator)
        self._module_id = module_id

    @property
    def module(self) -> LegrandModule:
        """Return module."""
        return self.coordinator.data[self._module_id]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        module = self.module

        if module.bridge is None:
            return {
                "identifiers": {(DOMAIN, module.id)},
                "manufacturer": MANUFACTURER,
                "model": "EcoMeter",
                "name": module.name,
            }

        return {
            "identifiers": {(DOMAIN, module.id)},
            "manufacturer": MANUFACTURER,
            "model": "EcoMeter Circuit",
            "name": module.name,
        }