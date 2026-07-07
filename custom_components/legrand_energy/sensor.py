"""Sensors for Legrand Energy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import LegrandEnergyCoordinator
from .models import LegrandModule


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Legrand Energy sensors."""
    coordinator: LegrandEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        LegrandEnergyCircuitSensor(coordinator, module_id)
        for module_id in coordinator.data
    ]

    async_add_entities(entities)


class LegrandEnergyCircuitSensor(
    CoordinatorEntity[LegrandEnergyCoordinator],
    SensorEntity,
):
    """Legrand circuit discovery sensor."""

    _attr_icon = "mdi:lightning-bolt-circle"

    def __init__(
        self,
        coordinator: LegrandEnergyCoordinator,
        module_id: str,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)

        self._module_id = module_id
        module = self.module

        self._attr_name = module.name
        self._attr_unique_id = (
            f"{DOMAIN}_{module_id}_circuit"
            .replace(":", "_")
            .replace("#", "_")
        )

        self._attr_device_info = {
            "identifiers": {(DOMAIN, module_id)},
            "name": module.name,
            "manufacturer": MANUFACTURER,
            "model": "Legrand EcoMeter",
            "via_device": (DOMAIN, module.bridge),
        }

    @property
    def module(self) -> LegrandModule:
        """Return current module."""
        return self.coordinator.data[self._module_id]

    @property
    def native_value(self) -> str:
        """Return sensor state."""
        return "detected"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return attributes."""
        module = self.module

        return {
            "module_id": module.id,
            "name": module.name,
            "type": module.type,
            "bridge": module.bridge,
        }