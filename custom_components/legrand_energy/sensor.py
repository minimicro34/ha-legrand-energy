"""Sensors for Legrand Energy integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LegrandEnergyCoordinator


SENSOR_TYPES = {
    "power": "Power",
    "energy": "Energy",
    "hp": "HP",
    "hc": "HC",
    "voltage": "Voltage",
    "current": "Current",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""

    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: LegrandEnergyCoordinator = data["coordinator"]

    entities = []

    for sensor_type in SENSOR_TYPES:
        entities.append(LegrandEnergySensor(coordinator, sensor_type))

    async_add_entities(entities)


class LegrandEnergySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Legrand Energy sensor."""

    def __init__(self, coordinator: LegrandEnergyCoordinator, sensor_type: str) -> None:
        super().__init__(coordinator)
        self.sensor_type = sensor_type

        self._attr_name = f"Legrand Energy {SENSOR_TYPES[sensor_type]}"
        self._attr_unique_id = f"legrand_energy_{sensor_type}"

    @property
    def native_value(self):
        """Return sensor value."""

        data = self.coordinator.data

        if not data:
            return None

        # ⚠️ Structure dépendante de l'API réelle
        energy = data.get("energy", {})
        status = data.get("status", {})

        # Placeholder logique (sera ajustée avec tes JSON réels)
        if self.sensor_type == "power":
            return status.get("power")

        if self.sensor_type == "energy":
            return energy.get("total_energy")

        if self.sensor_type == "hp":
            return energy.get("hp")

        if self.sensor_type == "hc":
            return energy.get("hc")

        if self.sensor_type == "voltage":
            return status.get("voltage")

        if self.sensor_type == "current":
            return status.get("current")

        return None

    @property
    def available(self) -> bool:
        """Sensor availability."""
        return self.coordinator.data is not None
