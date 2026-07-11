"""Sensor platform for Legrand Energy."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CURRENCY_EURO,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LegrandEnergyCoordinator
from .entity import LegrandEntity, get_main_module_id
from .models import (
    LegrandEnergyData,
    LegrandMeasurements,
    LegrandModule,
)

SensorValue = str | int | float | datetime | None
ValueFn = Callable[[LegrandEnergyData, LegrandModule | None], SensorValue]
AvailableFn = Callable[[LegrandEnergyData, LegrandModule | None], bool]
AttributesFn = Callable[
    [LegrandEnergyData, LegrandModule | None],
    dict[str, Any],
]


@dataclass(frozen=True, kw_only=True)
class LegrandSensorDescription(SensorEntityDescription):
    """Describe a Legrand Energy sensor."""

    module: bool = False
    value_fn: ValueFn
    available_fn: AvailableFn = lambda _data, _module: True
    attributes_fn: AttributesFn | None = None


def _format_remaining(remaining: timedelta | None) -> str | None:
    """Format a remaining duration as HH:MM."""
    if remaining is None:
        return None

    total_seconds = max(0, int(remaining.total_seconds()))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _seconds = divmod(remainder, 60)

    return f"{hours:02d}:{minutes:02d}"


def _remaining_until(next_change: datetime | None) -> timedelta | None:
    """Return the remaining duration until the next change."""
    if next_change is None:
        return None

    now = datetime.now(next_change.tzinfo)
    return max(next_change - now, timedelta())


def _tariff_attributes(
    data: LegrandEnergyData,
    _module: LegrandModule | None,
) -> dict[str, Any]:
    """Return attributes for the current tariff sensor."""
    if data.tariff is None:
        return {}

    return {
        "next_change": data.tariff.next_change,
        "remaining": _format_remaining(_remaining_until(data.tariff.next_change)),
    }


def _module_measurements(
    data: LegrandEnergyData,
    module: LegrandModule | None,
) -> LegrandMeasurements | None:
    """Return measurements for a module."""
    if module is None:
        return None

    return data.measurements_by_module.get(module.id)


def _module_energy_available(
    data: LegrandEnergyData,
    module: LegrandModule | None,
) -> bool:
    """Return whether energy data is available for a module."""
    measurements = _module_measurements(data, module)

    return measurements is not None and measurements.energy_today is not None


def _module_cost_available(
    data: LegrandEnergyData,
    module: LegrandModule | None,
) -> bool:
    """Return whether cost data is available for a module."""
    measurements = _module_measurements(data, module)

    return measurements is not None and measurements.cost_today is not None


SENSOR_DESCRIPTIONS: tuple[LegrandSensorDescription, ...] = (
    # Global tariff sensors
    LegrandSensorDescription(
        key="current_tariff",
        translation_key="current_tariff",
        icon="mdi:clock-outline",
        value_fn=lambda data, _module: (
            data.tariff.price_type if data.tariff is not None else None
        ),
        available_fn=lambda data, _module: data.tariff is not None,
        attributes_fn=_tariff_attributes,
    ),
    LegrandSensorDescription(
        key="current_price",
        translation_key="current_price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=f"{CURRENCY_EURO}/kWh",
        suggested_display_precision=4,
        value_fn=lambda data, _module: (
            data.tariff.price if data.tariff is not None else None
        ),
        available_fn=lambda data, _module: (
            data.tariff is not None and data.tariff.price is not None
        ),
    ),
    LegrandSensorDescription(
        key="next_tariff_change",
        translation_key="next_tariff_change",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data, _module: (
            data.tariff.next_change if data.tariff is not None else None
        ),
        available_fn=lambda data, _module: (
            data.tariff is not None and data.tariff.next_change is not None
        ),
    ),
    # Global measurements
    LegrandSensorDescription(
        key="power",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda data, _module: (
            data.measurements.power if data.measurements is not None else None
        ),
        available_fn=lambda data, _module: (
            data.measurements is not None and data.measurements.power is not None
        ),
    ),
    LegrandSensorDescription(
        key="energy_today",
        translation_key="energy_today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        value_fn=lambda data, _module: (
            data.measurements.energy_today if data.measurements is not None else None
        ),
        available_fn=lambda data, _module: (
            data.measurements is not None and data.measurements.energy_today is not None
        ),
    ),
    LegrandSensorDescription(
        key="energy_week",
        translation_key="energy_week",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        value_fn=lambda data, _module: (
            data.measurements.energy_week if data.measurements is not None else None
        ),
        available_fn=lambda data, _module: (
            data.measurements is not None and data.measurements.energy_week is not None
        ),
    ),
    LegrandSensorDescription(
        key="energy_month",
        translation_key="energy_month",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        value_fn=lambda data, _module: (
            data.measurements.energy_month if data.measurements is not None else None
        ),
        available_fn=lambda data, _module: (
            data.measurements is not None and data.measurements.energy_month is not None
        ),
    ),
    LegrandSensorDescription(
        key="energy_year",
        translation_key="energy_year",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        value_fn=lambda data, _module: (
            data.measurements.energy_year if data.measurements is not None else None
        ),
        available_fn=lambda data, _module: (
            data.measurements is not None and data.measurements.energy_year is not None
        ),
    ),
    LegrandSensorDescription(
        key="cost_today",
        translation_key="cost_today",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_EURO,
        suggested_display_precision=2,
        value_fn=lambda data, _module: (
            data.measurements.cost_today if data.measurements is not None else None
        ),
        available_fn=lambda data, _module: (
            data.measurements is not None and data.measurements.cost_today is not None
        ),
    ),
    LegrandSensorDescription(
        key="cost_peak_today",
        translation_key="cost_peak_today",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_EURO,
        suggested_display_precision=2,
        value_fn=lambda data, _module: (
            data.measurements.cost_peak_today if data.measurements is not None else None
        ),
        available_fn=lambda data, _module: (
            data.measurements is not None
            and data.measurements.cost_peak_today is not None
        ),
    ),
    LegrandSensorDescription(
        key="cost_off_peak_today",
        translation_key="cost_off_peak_today",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_EURO,
        suggested_display_precision=2,
        value_fn=lambda data, _module: (
            data.measurements.cost_off_peak_today
            if data.measurements is not None
            else None
        ),
        available_fn=lambda data, _module: (
            data.measurements is not None
            and data.measurements.cost_off_peak_today is not None
        ),
    ),
    LegrandSensorDescription(
        key="cost_week",
        translation_key="cost_week",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_EURO,
        suggested_display_precision=2,
        value_fn=lambda data, _module: (
            data.measurements.cost_week if data.measurements is not None else None
        ),
        available_fn=lambda data, _module: (
            data.measurements is not None and data.measurements.cost_week is not None
        ),
    ),
    LegrandSensorDescription(
        key="cost_month",
        translation_key="cost_month",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_EURO,
        suggested_display_precision=2,
        value_fn=lambda data, _module: (
            data.measurements.cost_month if data.measurements is not None else None
        ),
        available_fn=lambda data, _module: (
            data.measurements is not None and data.measurements.cost_month is not None
        ),
    ),
    LegrandSensorDescription(
        key="cost_year",
        translation_key="cost_year",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_EURO,
        suggested_display_precision=2,
        value_fn=lambda data, _module: (
            data.measurements.cost_year if data.measurements is not None else None
        ),
        available_fn=lambda data, _module: (
            data.measurements is not None and data.measurements.cost_year is not None
        ),
    ),
    # Global projections
    LegrandSensorDescription(
        key="projected_energy_today",
        translation_key="projected_energy_today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        value_fn=lambda data, _module: (
            data.projections.energy_end_of_day if data.projections is not None else None
        ),
        available_fn=lambda data, _module: (
            data.projections is not None
            and data.projections.energy_end_of_day is not None
        ),
    ),
    LegrandSensorDescription(
        key="projected_energy_month",
        translation_key="projected_energy_month",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        value_fn=lambda data, _module: (
            data.projections.energy_end_of_month
            if data.projections is not None
            else None
        ),
        available_fn=lambda data, _module: (
            data.projections is not None
            and data.projections.energy_end_of_month is not None
        ),
    ),
    LegrandSensorDescription(
        key="projected_cost_today",
        translation_key="projected_cost_today",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_EURO,
        suggested_display_precision=2,
        value_fn=lambda data, _module: (
            data.projections.cost_end_of_day if data.projections is not None else None
        ),
        available_fn=lambda data, _module: (
            data.projections is not None
            and data.projections.cost_end_of_day is not None
        ),
    ),
    LegrandSensorDescription(
        key="projected_cost_month",
        translation_key="projected_cost_month",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_EURO,
        suggested_display_precision=2,
        value_fn=lambda data, _module: (
            data.projections.cost_end_of_month if data.projections is not None else None
        ),
        available_fn=lambda data, _module: (
            data.projections is not None
            and data.projections.cost_end_of_month is not None
        ),
    ),
    # Contract diagnostics
    LegrandSensorDescription(
        key="contract_type",
        translation_key="contract_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:file-document-outline",
        value_fn=lambda data, _module: (
            data.contract.type if data.contract is not None else None
        ),
        available_fn=lambda data, _module: data.contract is not None,
    ),
    LegrandSensorDescription(
        key="contract_tariff",
        translation_key="contract_tariff",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:cash-clock",
        value_fn=lambda data, _module: (
            data.contract.tariff if data.contract is not None else None
        ),
        available_fn=lambda data, _module: data.contract is not None,
    ),
    LegrandSensorDescription(
        key="contract_option",
        translation_key="contract_option",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:tune",
        value_fn=lambda data, _module: (
            data.contract.tariff_option if data.contract is not None else None
        ),
        available_fn=lambda data, _module: data.contract is not None,
    ),
    LegrandSensorDescription(
        key="contract_power",
        translation_key="contract_power",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="kVA",
        icon="mdi:transmission-tower",
        value_fn=lambda data, _module: (
            data.contract.power_threshold if data.contract is not None else None
        ),
        available_fn=lambda data, _module: (
            data.contract is not None and data.contract.power_threshold is not None
        ),
    ),
    LegrandSensorDescription(
        key="peak_price",
        translation_key="peak_price",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=f"{CURRENCY_EURO}/kWh",
        suggested_display_precision=4,
        value_fn=lambda data, _module: (
            data.contract.peak_price if data.contract is not None else None
        ),
        available_fn=lambda data, _module: (
            data.contract is not None and data.contract.peak_price is not None
        ),
    ),
    LegrandSensorDescription(
        key="off_peak_price",
        translation_key="off_peak_price",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=f"{CURRENCY_EURO}/kWh",
        suggested_display_precision=4,
        value_fn=lambda data, _module: (
            data.contract.off_peak_price if data.contract is not None else None
        ),
        available_fn=lambda data, _module: (
            data.contract is not None and data.contract.off_peak_price is not None
        ),
    ),
    # Circuit measurements
    LegrandSensorDescription(
        key="circuit_energy_today",
        translation_key="circuit_energy_today",
        module=True,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        value_fn=lambda data, module: (
            measurements.energy_today
            if (
                measurements := _module_measurements(
                    data,
                    module,
                )
            )
            is not None
            else None
        ),
        available_fn=_module_energy_available,
    ),
    LegrandSensorDescription(
        key="circuit_cost_today",
        translation_key="circuit_cost_today",
        module=True,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_EURO,
        suggested_display_precision=2,
        value_fn=lambda data, module: (
            measurements.cost_today
            if (
                measurements := _module_measurements(
                    data,
                    module,
                )
            )
            is not None
            else None
        ),
        available_fn=_module_cost_available,
    ),
    LegrandSensorDescription(
        key="circuit_cost_peak_today",
        translation_key="circuit_cost_peak_today",
        module=True,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_EURO,
        suggested_display_precision=2,
        value_fn=lambda data, module: (
            measurements.cost_peak_today
            if (
                measurements := _module_measurements(
                    data,
                    module,
                )
            )
            is not None
            else None
        ),
        available_fn=lambda data, module: (
            (measurements := _module_measurements(data, module)) is not None
            and measurements.cost_peak_today is not None
        ),
    ),
    LegrandSensorDescription(
        key="circuit_cost_off_peak_today",
        translation_key="circuit_cost_off_peak_today",
        module=True,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=CURRENCY_EURO,
        suggested_display_precision=2,
        value_fn=lambda data, module: (
            measurements.cost_off_peak_today
            if (
                measurements := _module_measurements(
                    data,
                    module,
                )
            )
            is not None
            else None
        ),
        available_fn=lambda data, module: (
            (measurements := _module_measurements(data, module)) is not None
            and measurements.cost_off_peak_today is not None
        ),
    ),
    # Module diagnostics
    LegrandSensorDescription(
        key="module_type",
        translation_key="module_type",
        module=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:identifier",
        value_fn=lambda _data, module: module.type if module is not None else None,
        available_fn=lambda _data, module: module is not None and bool(module.type),
    ),
    LegrandSensorDescription(
        key="room",
        translation_key="room",
        module=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:home-outline",
        value_fn=lambda _data, module: module.room if module is not None else None,
        available_fn=lambda _data, module: (
            module is not None and module.room is not None
        ),
    ),
    LegrandSensorDescription(
        key="setup_date",
        translation_key="setup_date",
        module=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:calendar-clock",
        value_fn=lambda _data, module: (
            module.setup_date if module is not None else None
        ),
        available_fn=lambda _data, module: (
            module is not None and module.setup_date is not None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Legrand Energy sensors from a config entry."""
    coordinator: LegrandEnergyCoordinator = entry.runtime_data

    main_module_id = get_main_module_id(coordinator)

    if main_module_id is None:
        return

    entities: list[LegrandSensor] = []

    for description in SENSOR_DESCRIPTIONS:
        module_ids = (
            coordinator.data.modules if description.module else (main_module_id,)
        )

        entities.extend(
            LegrandSensor(
                coordinator=coordinator,
                module_id=module_id,
                description=description,
            )
            for module_id in module_ids
        )

    async_add_entities(entities)


class LegrandSensor(LegrandEntity, SensorEntity):
    """Represent a Legrand Energy sensor."""

    entity_description: LegrandSensorDescription

    def __init__(
        self,
        coordinator: LegrandEnergyCoordinator,
        module_id: str,
        description: LegrandSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, module_id)

        self.entity_description = description
        self._attr_unique_id = f"{module_id}_{description.key}"

    @property
    def native_value(self) -> SensorValue:
        """Return the current sensor value."""
        return self.entity_description.value_fn(
            self.coordinator.data,
            self.module,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        attributes_fn = self.entity_description.attributes_fn

        if attributes_fn is None:
            return None

        attributes = attributes_fn(
            self.coordinator.data,
            self.module,
        )
        return attributes or None

    @property
    def available(self) -> bool:
        """Return whether the sensor is available."""
        return super().available and self.entity_description.available_fn(
            self.coordinator.data,
            self.module,
        )
