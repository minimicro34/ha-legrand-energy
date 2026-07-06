"""Sensors for Legrand Energy."""

from __future__ import annotations

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
from .models import ModuleMeasurement


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    for module_id, module in coordinator.data.items():
        entities.append(LegrandEnergyEnergySensor(coordinator, module_id, module))
        entities.append(LegrandEnergyPriceSensor(coordinator, module_id, module))

    async_add_entities(entities)


class LegrandEnergyBaseSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, module_id: str, module: ModuleMeasurement) -> None:
        super().__init__(coordinator)
        self._module_id = module_id
        self._module_name = module.name

        self._attr_device_info = {
            "identifiers": {(DOMAIN, module_id)},
            "name": module.name,
            "manufacturer": MANUFACTURER,
            "model": "Drivia with Netatmo / Ecometer",
            "via_device": (DOMAIN, module.bridge) if module.bridge else None,
        }

    @property
    def module(self) -> ModuleMeasurement | None:
        return self.coordinator.data.get(self._module_id)


class LegrandEnergyEnergySensor(LegrandEnergyBaseSensor):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR

    def __init__(self, coordinator, module_id: str, module: ModuleMeasurement) -> None:
        super().__init__(coordinator, module_id, module)
        self._attr_name = f"{module.name} énergie"
        self._attr_unique_id = f"{DOMAIN}_{module_id}_energy".replace(":", "_").replace("#", "_")

    @property
    def native_value(self):
        module = self.module
        if module is None or module.latest is None:
            return None
        return module.energy

    @property
    def extra_state_attributes(self):
        module = self.module
        return {
            "module_id": self._module_id,
            "latest_timestamp": module.latest.timestamp if module and module.latest else None,
            "raw_values": module.latest.values if module and module.latest else {},
        }


class LegrandEnergyPriceSensor(LegrandEnergyBaseSensor):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "EUR"

    def __init__(self, coordinator, module_id: str, module: ModuleMeasurement) -> None:
        super().__init__(coordinator, module_id, module)
        self._attr_name = f"{module.name} coût"
        self._attr_unique_id = f"{DOMAIN}_{module_id}_price".replace(":", "_").replace("#", "_")

    @property
    def native_value(self):
        module = self.module
        if module is None or module.latest is None:
            return None
        return round(module.price, 6)

    @property
    def extra_state_attributes(self):
        module = self.module
        return {
            "module_id": self._module_id,
            "latest_timestamp": module.latest.timestamp if module and module.latest else None,
            "raw_values": module.latest.values if module and module.latest else {},
        }