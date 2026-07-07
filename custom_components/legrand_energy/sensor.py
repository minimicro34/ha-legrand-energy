"""Sensors for Legrand Energy."""

from __future__ import annotations

from typing import Any
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy
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

    entities = []

    for module_id in coordinator.data:
        entities.extend(
        (
            LegrandEnergyEnergyTariff1Sensor(coordinator, module_id),
            LegrandEnergyEnergyTariff2Sensor(coordinator, module_id),
            LegrandEnergyPriceTariff1Sensor(coordinator, module_id),
            LegrandEnergyPriceTariff2Sensor(coordinator, module_id),
        )
    )

    async_add_entities(entities)

class LegrandEnergyMeasureSensor(
    LegrandEntity,
    SensorEntity,
):
    """Base measurement sensor."""

    _attr_should_poll = False

    def __init__(self, coordinator, module_id):
        super().__init__(coordinator, module_id)

        self._attr_has_entity_name = True

class LegrandEnergyEnergyTariff1Sensor(
    LegrandEnergyMeasureSensor,
):
    _attr_translation_key = "energy_tariff1"

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR

    @property
    def unique_id(self):
        return f"{self.module.id}_energy_tariff1"

    @property
    def native_value(self):
        return self.module.energy_tariff1

class LegrandEnergyEnergyTariff2Sensor(
    LegrandEnergyMeasureSensor,
):
    _attr_translation_key = "energy_tariff2"

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR

    @property
    def unique_id(self):
        return f"{self.module.id}_energy_tariff2"

    @property
    def native_value(self):
        return self.module.energy_tariff2

class LegrandEnergyPriceTariff1Sensor(
    LegrandEnergyMeasureSensor,
):
    _attr_translation_key = "price_tariff1"

    @property
    def unique_id(self):
        return f"{self.module.id}_price_tariff1"

    @property
    def native_value(self):
        return self.module.price_tariff1

class LegrandEnergyPriceTariff2Sensor(
    LegrandEnergyMeasureSensor,
):
    _attr_translation_key = "price_tariff2"

    @property
    def unique_id(self):
        return f"{self.module.id}_price_tariff2"

    @property
    def native_value(self):
        return self.module.price_tariff2

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
