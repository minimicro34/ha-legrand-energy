"""Contract sensors for Legrand Energy."""

from __future__ import annotations

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
    """Set up contract sensors."""
    coordinator: LegrandEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]

    bridge_id = next(
        (module_id for module_id, module in coordinator.data.items() if module.bridge is None),
        None,
    )

    if bridge_id is None:
        return

    async_add_entities(
        [
            LegrandContractTypeSensor(coordinator, bridge_id),
            LegrandContractTariffSensor(coordinator, bridge_id),
            LegrandContractOptionSensor(coordinator, bridge_id),
            LegrandContractPowerSensor(coordinator, bridge_id),
            LegrandContractPeakPriceSensor(coordinator, bridge_id),
            LegrandContractOffPeakPriceSensor(coordinator, bridge_id),
        ]
    )


class LegrandContractSensor(LegrandEntity, SensorEntity):
    """Base contract sensor."""

    _attr_entity_category = "diagnostic"

    @property
    def contract(self):
        """Return contract."""
        return self.coordinator.contract

    @property
    def available(self) -> bool:
        """Return availability."""
        return self.contract is not None and super().available


class LegrandContractTypeSensor(LegrandContractSensor):
    """Contract type sensor."""

    _attr_translation_key = "contract_type"

    def __init__(self, coordinator: LegrandEnergyCoordinator, module_id: str) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, module_id)
        self._attr_unique_id = f"{DOMAIN}_{module_id}_contract_type".replace(":", "_")

    @property
    def native_value(self) -> str | None:
        """Return value."""
        return self.contract.type if self.contract else None


class LegrandContractTariffSensor(LegrandContractSensor):
    """Contract tariff sensor."""

    _attr_translation_key = "contract_tariff"

    def __init__(self, coordinator: LegrandEnergyCoordinator, module_id: str) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, module_id)
        self._attr_unique_id = f"{DOMAIN}_{module_id}_contract_tariff".replace(":", "_")

    @property
    def native_value(self) -> str | None:
        """Return value."""
        return self.contract.tariff if self.contract else None


class LegrandContractOptionSensor(LegrandContractSensor):
    """Contract option sensor."""

    _attr_translation_key = "contract_option"

    def __init__(self, coordinator: LegrandEnergyCoordinator, module_id: str) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, module_id)
        self._attr_unique_id = f"{DOMAIN}_{module_id}_contract_option".replace(":", "_")

    @property
    def native_value(self) -> str | None:
        """Return value."""
        return self.contract.tariff_option if self.contract else None


class LegrandContractPowerSensor(LegrandContractSensor):
    """Contract power sensor."""

    _attr_translation_key = "contract_power"
    _attr_native_unit_of_measurement = "kVA"

    def __init__(self, coordinator: LegrandEnergyCoordinator, module_id: str) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, module_id)
        self._attr_unique_id = f"{DOMAIN}_{module_id}_contract_power".replace(":", "_")

    @property
    def native_value(self) -> float | None:
        """Return value."""
        return self.contract.power_threshold if self.contract else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return unit."""
        return self.contract.power_unit if self.contract else "kVA"


class LegrandContractPeakPriceSensor(LegrandContractSensor):
    """Peak price sensor."""

    _attr_translation_key = "peak_price"
    _attr_native_unit_of_measurement = "€/kWh"

    def __init__(self, coordinator: LegrandEnergyCoordinator, module_id: str) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, module_id)
        self._attr_unique_id = f"{DOMAIN}_{module_id}_peak_price".replace(":", "_")

    @property
    def native_value(self) -> float | None:
        """Return value."""
        return self.contract.peak_price if self.contract else None


class LegrandContractOffPeakPriceSensor(LegrandContractSensor):
    """Off-peak price sensor."""

    _attr_translation_key = "off_peak_price"
    _attr_native_unit_of_measurement = "€/kWh"

    def __init__(self, coordinator: LegrandEnergyCoordinator, module_id: str) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, module_id)
        self._attr_unique_id = f"{DOMAIN}_{module_id}_off_peak_price".replace(":", "_")

    @property
    def native_value(self) -> float | None:
        """Return value."""
        return self.contract.off_peak_price if self.contract else None