"""Sensors for Legrand Energy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Legrand Energy sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    modules = coordinator.data.get("modules", {})

    entities = [
        LegrandEnergySensor(coordinator, module_id, module)
        for module_id, module in modules.items()
    ]

    async_add_entities(entities)


class LegrandEnergySensor(CoordinatorEntity, SensorEntity):
    """Legrand Energy sensor."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def __init__(
        self,
        coordinator,
        module_id: str,
        module: dict[str, Any],
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)

        self._module_id = module_id
        self._module = module

        name = module.get("name", module_id)

        self._attr_name = f"Legrand Energy {name}"
        self._attr_unique_id = f"{DOMAIN}_{module_id}_energy".replace(":", "_").replace("#", "_")

        self._attr_device_info = {
            "identifiers": {(DOMAIN, module.get("bridge") or module_id)},
            "name": "Legrand Ecometer",
            "manufacturer": MANUFACTURER,
            "model": "Drivia with Netatmo / Ecometer",
        }

    @property
    def native_value(self):
        """Return sensor value."""
        module = self.coordinator.data.get("modules", {}).get(self._module_id)

        if module is None:
            return None

        value = module.get("energy")

        if value is None:
            return None

        return value

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        module = self.coordinator.data.get("modules", {}).get(self._module_id, {})

        return {
            "module_id": self._module_id,
            "home_id": module.get("home_id"),
            "home_name": module.get("home_name"),
            "bridge": module.get("bridge"),
            "measure_type": "sum_energy_buy_from_grid",
        }