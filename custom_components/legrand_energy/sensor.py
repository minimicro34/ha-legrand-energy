"""Sensors for Legrand Energy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LegrandEnergyCoordinator
from .entity import LegrandEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Legrand Energy sensors."""
    coordinator: LegrandEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        LegrandEnergyCircuitSensor(coordinator, module_id)
        for module_id in coordinator.data
    )


class LegrandEnergyCircuitSensor(LegrandEntity, SensorEntity):
    """Representation of a Legrand circuit."""

    _attr_icon = "mdi:flash"

    def __init__(
        self,
        coordinator: LegrandEnergyCoordinator,
        module_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, module_id)

        module = self.module
        self._attr_name = module.name
        self._attr_unique_id = f"{DOMAIN}_{module.id}".replace(":", "_").replace("#", "_")

    @property
    def native_value(self) -> str:
        """Return the sensor state."""
        return "detected"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        module = self.module

        return {
            "module_id": module.id,
            "type": module.type,
            "bridge": module.bridge,
            "room": module.room,
        }
