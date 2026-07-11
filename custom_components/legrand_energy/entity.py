"""Base entity for Legrand Energy."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import LegrandEnergyCoordinator
from .models import LegrandModule


def get_main_module_id(
    coordinator: LegrandEnergyCoordinator,
) -> str | None:
    """Return the physical EcoMeter module ID."""
    modules = coordinator.data.modules

    # The physical EcoMeter has the unsuffixed module ID.
    # Circuits use IDs such as <bridge>#0, <bridge>#1, etc.
    for module_id, module in modules.items():
        if module.type == "NLE" and "#" not in module_id:
            return module_id

    # Fallback: find a module referenced as the bridge by a child circuit.
    referenced_bridges = {
        module.bridge for module in modules.values() if module.bridge is not None
    }

    for module_id in modules:
        if module_id in referenced_bridges:
            return module_id

    return None


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
        main_module_id = get_main_module_id(coordinator)

        is_main_module = module_id == main_module_id

        device_info = DeviceInfo(
            identifiers={(DOMAIN, module.id)},
            manufacturer=MANUFACTURER,
            model=("EcoMeter" if is_main_module else "EcoMeter Circuit"),
            name=module.name,
        )

        if not is_main_module and module.bridge is not None:
            device_info["via_device"] = (
                DOMAIN,
                module.bridge,
            )

        self._attr_device_info = device_info

    @property
    def module(self) -> LegrandModule | None:
        """Return the current module."""
        return self.coordinator.data.modules.get(self._module_id)

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return super().available and self._module_id in self.coordinator.data.modules
