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


#
# Dernier intervalle reçu
#
# Ces valeurs ne sont pas des compteurs croissants.
# On ne définit donc pas de state_class.
#

ENERGY_DESCRIPTIONS: tuple[LegrandSensorDescription, ...] = (
    LegrandSensorDescription(
        key="energy_tariff1",
        translation_key="energy_tariff1",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda module: (
            module.energy_tariff1 / 1000
            if module.energy_tariff1 is not None
            else None
        ),
    ),
    LegrandSensorDescription(
        key="energy_tariff2",
        translation_key="energy_tariff2",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda module: (
            module.energy_tariff2 / 1000
            if module.energy_tariff2 is not None
            else None
        ),
    ),
    LegrandSensorDescription(
        key="price_tariff1",
        translation_key="price_tariff1",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="€",
        suggested_display_precision=4,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda module: module.price_tariff1,
    ),
    LegrandSensorDescription(
        key="price_tariff2",
        translation_key="price_tariff2",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="€",
        suggested_display_precision=4,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda module: module.price_tariff2,
    ),
)


#
# Fenêtre glissante des dernières 24 heures
#

STATISTICS_DESCRIPTIONS: tuple[LegrandSensorDescription, ...] = (
    LegrandSensorDescription(
        key="energy_total",
        translation_key="energy_total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda module: (
            module.statistics.total_energy / 1000
            if module.statistics is not None
            else None
        ),
    ),
    LegrandSensorDescription(
        key="energy_cost",
        translation_key="energy_cost",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="€",
        suggested_display_precision=2,
        value_fn=lambda module: (
            module.statistics.total_cost
            if module.statistics is not None
            else None
        ),
    ),
)


#
# Journée civile locale depuis minuit
#

DAILY_DESCRIPTIONS: tuple[LegrandSensorDescription, ...] = (
    LegrandSensorDescription(
        key="energy_today",
        translation_key="energy_today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda module: (
            module.statistics.daily.total_energy / 1000
            if module.statistics is not None
            and module.statistics.daily is not None
            else None
        ),
    ),
    LegrandSensorDescription(
        key="cost_today",
        translation_key="cost_today",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="€",
        suggested_display_precision=2,
        value_fn=lambda module: (
            module.statistics.daily.total_cost
            if module.statistics is not None
            and module.statistics.daily is not None
            else None
        ),
    ),
    LegrandSensorDescription(
        key="energy_peak_today",
        translation_key="energy_peak_today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda module: (
            module.statistics.daily.peak_energy / 1000
            if module.statistics is not None
            and module.statistics.daily is not None
            else None
        ),
    ),
    LegrandSensorDescription(
        key="energy_off_peak_today",
        translation_key="energy_off_peak_today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda module: (
            module.statistics.daily.off_peak_energy / 1000
            if module.statistics is not None
            and module.statistics.daily is not None
            else None
        ),
    ),
    LegrandSensorDescription(
        key="cost_peak_today",
        translation_key="cost_peak_today",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="€",
        suggested_display_precision=2,
        value_fn=lambda module: (
            module.statistics.daily.peak_cost
            if module.statistics is not None
            and module.statistics.daily is not None
            else None
        ),
    ),
    LegrandSensorDescription(
        key="cost_off_peak_today",
        translation_key="cost_off_peak_today",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="€",
        suggested_display_precision=2,
        value_fn=lambda module: (
            module.statistics.daily.off_peak_cost
            if module.statistics is not None
            and module.statistics.daily is not None
            else None
        ),
    ),
    LegrandSensorDescription(
        key="projected_energy_today",
        translation_key="projected_energy_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda module: (
            module.statistics.projection.projected_energy / 1000
            if module.statistics is not None
            and module.statistics.projection is not None
            else None
        ),
    ),
    LegrandSensorDescription(
        key="projected_cost_today",
        translation_key="projected_cost_today",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="€",
        suggested_display_precision=2,
        value_fn=lambda module: (
            module.statistics.projection.projected_cost
            if module.statistics is not None
            and module.statistics.projection is not None
            else None
        ),
    ),
    LegrandSensorDescription(
        key="projected_monthly_cost",
        translation_key="projected_monthly_cost",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="€",
        suggested_display_precision=2,
        value_fn=lambda module: (
            module.statistics.monthly_projection.projected_cost
            if module.statistics is not None
            and module.statistics.monthly_projection is not None
            else None
        ),
    ),
)


#
# Contrat
#

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
        suggested_display_precision=0,
        contract_value_fn=lambda contract: contract.power_threshold,
    ),
    LegrandSensorDescription(
        key="peak_price",
        translation_key="peak_price",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="€/kWh",
        suggested_display_precision=4,
        contract_value_fn=lambda contract: contract.peak_price,
    ),
    LegrandSensorDescription(
        key="off_peak_price",
        translation_key="off_peak_price",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="€/kWh",
        suggested_display_precision=4,
        contract_value_fn=lambda contract: contract.off_peak_price,
    ),
)


#
# Tarif actuel
#

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
        suggested_display_precision=4,
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

        if suffix > 5:
            continue

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
        self._attr_has_entity_name = True

        safe_module_id = module_id.replace(":", "_").replace("#", "_")
        self._attr_unique_id = (
            f"{DOMAIN}_{safe_module_id}_{description.key}"
        )


class LegrandEnergySensor(LegrandBaseSensor):
    """Last interval energy sensor."""

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        value_fn = self.entity_description.value_fn

        if value_fn is None:
            return None

        return value_fn(self.module)


class LegrandStatisticsSensor(LegrandBaseSensor):
    """Calculated statistics sensor."""

    @property
    def available(self) -> bool:
        """Return availability."""
        return (
            super().available
            and self.module.statistics is not None
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        value_fn = self.entity_description.value_fn

        if value_fn is None:
            return None

        return value_fn(self.module)


class LegrandContractSensor(LegrandBaseSensor):
    """Contract sensor."""

    @property
    def available(self) -> bool:
        """Return availability."""
        return (
            super().available
            and self.coordinator.contract is not None
        )

    @property
    def native_value(self) -> Any:
        """Return the contract value."""
        contract = self.coordinator.contract
        value_fn = self.entity_description.contract_value_fn

        if contract is None or value_fn is None:
            return None

        return value_fn(contract)


class LegrandTariffSensor(LegrandBaseSensor):
    """Current tariff sensor."""

    @property
    def available(self) -> bool:
        """Return availability."""
        return (
            super().available
            and self.coordinator.tariff_engine is not None
        )

    @property
    def native_value(self) -> Any:
        """Return the tariff value."""
        engine = self.coordinator.tariff_engine
        value_fn = self.entity_description.tariff_value_fn

        if engine is None or value_fn is None:
            return None

        return value_fn(engine)