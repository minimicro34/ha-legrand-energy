"""Base entity for Legrand Energy."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import LegrandEnergyCoordinator
from .models import LegrandModule


class LegrandEntity(CoordinatorEntity[LegrandEnergyCoordinator]):
    """Base entity for a Legrand Energy module."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LegrandEnergyCoordinator,
        module_id: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)

        self._module_id = module_id
        module = coordinator.data.modules[module_id]

        device_info = DeviceInfo(
            identifiers={(DOMAIN, module.id)},
            manufacturer=MANUFACTURER,
            model=("EcoMeter Circuit" if module.bridge is not None else "EcoMeter"),
            name=module.name,
        )

        if module.bridge is not None:
            device_info["via_device"] = (DOMAIN, module.bridge)

        self._attr_device_info = device_info

    @property
    def module(self) -> LegrandModule | None:
        """Return the current module."""
        return self.coordinator.data.modules.get(self._module_id)

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return super().available and self._module_id in self.coordinator.data.modules
