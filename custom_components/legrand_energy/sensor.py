"""Sensors for Legrand Energy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LegrandEnergyCoordinator
from .entity import LegrandEntity
from .models import LegrandModule
from .tariff_engine import TariffEngine


@dataclass(frozen=True, kw_only=True)
class LegrandSensorDescription(SensorEntityDescription):
    """Legrand sensor description."""

    value_fn: Callable[[LegrandModule], Any] | None = None
    contract_value_fn: Callable[[Any], Any] | None = None
    tariff_value_fn: Callable[[TariffEngine], Any] | None = None


ENERGY_DESCRIPTIONS: tuple[LegrandSensorDescription, ...] = (
    LegrandSensorDescription(
        key="energy_tariff1",
        translation_key="energy_tariff1",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        value_fn=lambda module: getattr(module, "energy_tariff1", None),
    ),
    LegrandSensorDescription(
        key="energy_tariff2",
        translation_key="energy_tariff2",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        value_fn=lambda module: getattr(module, "energy_tariff2", None),
    ),
    LegrandSensorDescription(
        key="price_tariff1",
        translation_key="price_tariff1",
        native_unit_of_measurement="€",
        value_fn=lambda module: getattr(module, "price_tariff1", None),
    ),
    LegrandSensorDescription(
        key="price_tariff2",
        translation_key="price_tariff2",
        native_unit_of_measurement="€",
        value_fn=lambda module: getattr(module, "price_tariff2", None),
    ),
)

STATISTICS_DESCRIPTIONS: tuple[LegrandSensorDescription, ...] = (
    LegrandSensorDescription(
        key="energy_total",
        translation_key="energy_total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        value_fn=lambda module: (
            module.statistics.total_energy if module.statistics else None
        ),
    ),
    LegrandSensorDescription(
        key="energy_cost",
        translation_key="energy_cost",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="€",
        value_fn=lambda module: (
            module.statistics.total_cost if module.statistics else None
        ),
    ),
)

DAILY_DESCRIPTIONS: tuple[LegrandSensorDescription, ...] = (
    LegrandSensorDescription(
        key="energy_today",
        translation_key="energy_today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        value_fn=lambda module: (
            module.statistics.daily.total_energy
            if module.statistics and module.statistics.daily
            else None
        ),
    ),
    LegrandSensorDescription(
        key="cost_today",
        translation_key="cost_today",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="€",
        value_fn=lambda module: (
            module.statistics.daily.total_cost
            if module.statistics and module.statistics.daily
            else None
        ),
    ),
    LegrandSensorDescription(
        key="projected_energy_today",
        translation_key="projected_energy_today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        value_fn=lambda module: (
            module.statistics.projection.projected_energy
            if module.statistics and module.statistics.projection
            else None
        ),
    ),
    LegrandSensorDescription(
        key="projected_cost_today",
        translation_key="projected_cost_today",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="€",
        value_fn=lambda module: (
            module.statistics.projection.projected_cost
            if module.statistics and module.statistics.projection
            else None
        ),
    ),
    LegrandSensorDescription(
        key="energy_peak_today",
        translation_key="energy_peak_today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        value_fn=lambda module: (
            module.statistics.daily.peak_energy
            if module.statistics and module.statistics.daily
            else None
        ),
    ),
    LegrandSensorDescription(
        key="energy_off_peak_today",
        translation_key="energy_off_peak_today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        value_fn=lambda module: (
            module.statistics.daily.off_peak_energy
            if module.statistics and module.statistics.daily
            else None
        ),
    ),
    LegrandSensorDescription(
        key="cost_peak_today",
        translation_key="cost_peak_today",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="€",
        value_fn=lambda module: (
            module.statistics.daily.peak_cost
            if module.statistics and module.statistics.daily
            else None
        ),
    ),
    LegrandSensorDescription(
        key="cost_off_peak_today",
        translation_key="cost_off_peak_today",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="€",
        value_fn=lambda module: (
            module.statistics.daily.off_peak_cost
            if module.statistics and module.statistics.daily
            else None
        ),
    ),
    LegrandSensorDescription(
        key="projected_monthly_cost",
        translation_key="projected_monthly_cost",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="€",
        value_fn=lambda module: (
            module.statistics.monthly_projection.projected_cost
            if module.statistics and module.statistics.monthly_projection
            else None
        ),
    ),
)

CONTRACT_DESCRIPTIONS: tuple[LegrandSensorDescription, ...] = (
    LegrandSensorDescription(
        key="contract_type",
        translation_key="contract_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        contract_value_fn=lambda contract: contract.type,
    ),
    LegrandSensorDescription(
        key="contract_tariff",
        translation_key="contract_tariff",
        entity_category=EntityCategory.DIAGNOSTIC,
        contract_value_fn=lambda contract: contract.tariff,
    ),
    LegrandSensorDescription(
        key="contract_option",
        translation_key="contract_option",
        entity_category=EntityCategory.DIAGNOSTIC,
        contract_value_fn=lambda contract: contract.tariff_option,
    ),
    LegrandSensorDescription(
        key="contract_power",
        translation_key="contract_power",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="kVA",
        contract_value_fn=lambda contract: contract.power_threshold,
    ),
    LegrandSensorDescription(
        key="peak_price",
        translation_key="peak_price",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="€/kWh",
        contract_value_fn=lambda contract: contract.peak_price,
    ),
    LegrandSensorDescription(
        key="off_peak_price",
        translation_key="off_peak_price",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="€/kWh",
        contract_value_fn=lambda contract: contract.off_peak_price,
    ),
)

TARIFF_DESCRIPTIONS: tuple[LegrandSensorDescription, ...] = (
    LegrandSensorDescription(
        key="current_tariff",
        translation_key="current_tariff",
        tariff_value_fn=lambda engine: engine.current_zone(),
    ),
    LegrandSensorDescription(
        key="current_price",
        translation_key="current_price",
        native_unit_of_measurement="€/kWh",
        tariff_value_fn=lambda engine: engine.current_price(),
    ),
    LegrandSensorDescription(
        key="next_tariff_change",
        translation_key="next_tariff_change",
        device_class=SensorDeviceClass.TIMESTAMP,
        tariff_value_fn=lambda engine: engine.next_change(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Legrand Energy sensors."""
    coordinator: LegrandEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    for module_id, module in coordinator.data.items():
        if module.bridge is None:
            continue

        try:
            suffix = int(module_id.rsplit("#", 1)[1])
        except (IndexError, ValueError):
            continue

        if suffix <= 5:
            for description in ENERGY_DESCRIPTIONS:
                entities.append(
                    LegrandEnergySensor(
                        coordinator=coordinator,
                        module_id=module_id,
                        description=description,
                    )
                )

            for description in STATISTICS_DESCRIPTIONS:
                entities.append(
                    LegrandStatisticsSensor(
                        coordinator=coordinator,
                        module_id=module_id,
                        description=description,
                    )
                )

            for description in DAILY_DESCRIPTIONS:
                entities.append(
                    LegrandStatisticsSensor(
                        coordinator=coordinator,
                        module_id=module_id,
                        description=description,
                    )
                )

    bridge_id = next(
        (
            module_id
            for module_id, module in coordinator.data.items()
            if module.bridge is None
        ),
        None,
    )

    if bridge_id is not None:
        for description in CONTRACT_DESCRIPTIONS:
            entities.append(
                LegrandContractSensor(
                    coordinator=coordinator,
                    module_id=bridge_id,
                    description=description,
                )
            )

        for description in TARIFF_DESCRIPTIONS:
            entities.append(
                LegrandTariffSensor(
                    coordinator=coordinator,
                    module_id=bridge_id,
                    description=description,
                )
            )

    async_add_entities(entities)


class LegrandBaseSensor(LegrandEntity, SensorEntity):
    """Base Legrand sensor."""

    entity_description: LegrandSensorDescription

    def __init__(
        self,
        coordinator: LegrandEnergyCoordinator,
        module_id: str,
        description: LegrandSensorDescription,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, module_id)
        self.entity_description = description
        safe_module_id = module_id.replace(":", "_").replace("#", "_")
        self._attr_unique_id = f"{DOMAIN}_{safe_module_id}_{description.key}"
        self._attr_has_entity_name = True


class LegrandEnergySensor(LegrandBaseSensor):
    """Energy sensor."""

    @property
    def native_value(self) -> Any:
        """Return value."""
        if self.entity_description.value_fn is None:
            return None
        return self.entity_description.value_fn(self.module)


class LegrandStatisticsSensor(LegrandBaseSensor):
    """Statistics sensor."""

    @property
    def available(self) -> bool:
        """Return availability."""
        return super().available and self.module.statistics is not None

    @property
    def native_value(self) -> Any:
        """Return value."""
        if self.entity_description.value_fn is None:
            return None
        return self.entity_description.value_fn(self.module)


class LegrandContractSensor(LegrandBaseSensor):
    """Contract sensor."""

    @property
    def available(self) -> bool:
        """Return availability."""
        return super().available and self.coordinator.contract is not None

    @property
    def native_value(self) -> Any:
        """Return value."""
        contract = self.coordinator.contract
        if contract is None or self.entity_description.contract_value_fn is None:
            return None
        return self.entity_description.contract_value_fn(contract)

class LegrandTariffSensor(LegrandBaseSensor):
    """Tariff sensor."""

    @property
    def available(self) -> bool:
        """Return availability."""
        return super().available and self.coordinator.tariff_engine is not None

    @property
    def native_value(self) -> Any:
        """Return value."""
        engine = self.coordinator.tariff_engine

        if engine is None or self.entity_description.tariff_value_fn is None:
            return None

        return self.entity_description.tariff_value_fn(engine)