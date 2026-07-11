"""Sensor platform for Legrand Energy."""

from __future__ import annotations

from collections.abc import Callable, Mapping
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
from homeassistant.const import CURRENCY_EURO, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import LegrandEnergyCoordinator
from .entity import LegrandEntity, get_main_module_id
from .models import (
    LegrandEnergyData,
    LegrandMeasurements,
    LegrandModule,
)

ValueFn = Callable[
    [LegrandEnergyData, LegrandModule],
    str | int | float | datetime | None,
]

AvailableFn = Callable[
    [LegrandEnergyData, LegrandModule],
    bool,
]

AttributesFn = Callable[
    [LegrandEnergyData, LegrandModule],
    Mapping[str, Any] | None,
]


@dataclass(frozen=True, kw_only=True)
class LegrandSensorDescription(SensorEntityDescription):
    """Describe a Legrand Energy sensor."""

    value_fn: ValueFn
    available_fn: AvailableFn
    attributes_fn: AttributesFn | None = None
    module: bool = False


def _format_remaining(
    remaining: timedelta | None,
) -> str | None:
    """Format a remaining duration."""
    if remaining is None:
        return None

    total_seconds = max(
        0,
        int(remaining.total_seconds()),
    )

    hours, remainder = divmod(
        total_seconds,
        3600,
    )
    minutes, _seconds = divmod(
        remainder,
        60,
    )

    if hours > 0:
        return f"{hours} h {minutes:02d} min"

    return f"{minutes} min"


def _remaining_until(
    target: datetime | None,
) -> timedelta | None:
    """Return remaining time until a target datetime."""
    if target is None:
        return None

    return target - dt_util.now()


def _module_measurements(
    data: LegrandEnergyData,
    module: LegrandModule,
) -> LegrandMeasurements | None:
    """Return measurements for a module."""
    return data.measurements_by_module.get(module.id)


GLOBAL_SENSOR_DESCRIPTIONS: tuple[
    LegrandSensorDescription,
    ...,
] = (
    LegrandSensorDescription(
        key="current_tariff",
        translation_key="current_tariff",
        value_fn=lambda data, _module: (
            data.tariff.price_type if data.tariff is not None else None
        ),
        available_fn=lambda data, _module: data.tariff is not None,
        attributes_fn=lambda data, _module: (
            {
                "zone_id": data.tariff.zone_id,
                "zone_name": data.tariff.zone_name,
                "next_change": data.tariff.next_change,
                "remaining": _format_remaining(
                    _remaining_until(data.tariff.next_change)
                ),
            }
            if data.tariff is not None
            else None
        ),
    ),
    LegrandSensorDescription(
        key="current_price",
        translation_key="current_price",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=(f"{CURRENCY_EURO}/kWh"),
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
    LegrandSensorDescription(
        key="power",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=(UnitOfPower.WATT),
        state_class=(SensorStateClass.MEASUREMENT),
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
        native_unit_of_measurement=(UnitOfEnergy.KILO_WATT_HOUR),
        state_class=SensorStateClass.TOTAL,
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
        native_unit_of_measurement=(UnitOfEnergy.KILO_WATT_HOUR),
        state_class=SensorStateClass.TOTAL,
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
        native_unit_of_measurement=(UnitOfEnergy.KILO_WATT_HOUR),
        state_class=SensorStateClass.TOTAL,
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
        native_unit_of_measurement=(UnitOfEnergy.KILO_WATT_HOUR),
        state_class=SensorStateClass.TOTAL,
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
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
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
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
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
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
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
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
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
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
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
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data, _module: (
            data.measurements.cost_year if data.measurements is not None else None
        ),
        available_fn=lambda data, _module: (
            data.measurements is not None and data.measurements.cost_year is not None
        ),
    ),
    LegrandSensorDescription(
        key="projected_energy_today",
        translation_key="projected_energy_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=(UnitOfEnergy.KILO_WATT_HOUR),
        state_class=SensorStateClass.TOTAL,
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
        native_unit_of_measurement=(UnitOfEnergy.KILO_WATT_HOUR),
        state_class=SensorStateClass.TOTAL,
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
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
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
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data, _module: (
            data.projections.cost_end_of_month if data.projections is not None else None
        ),
        available_fn=lambda data, _module: (
            data.projections is not None
            and data.projections.cost_end_of_month is not None
        ),
    ),
    LegrandSensorDescription(
        key="contract_type",
        translation_key="contract_type",
        value_fn=lambda data, _module: (
            data.contract.type if data.contract is not None else None
        ),
        available_fn=lambda data, _module: (
            data.contract is not None and bool(data.contract.type)
        ),
    ),
    LegrandSensorDescription(
        key="contract_tariff",
        translation_key="contract_tariff",
        value_fn=lambda data, _module: (
            data.contract.tariff if data.contract is not None else None
        ),
        available_fn=lambda data, _module: (
            data.contract is not None and bool(data.contract.tariff)
        ),
    ),
    LegrandSensorDescription(
        key="contract_option",
        translation_key="contract_option",
        value_fn=lambda data, _module: (
            data.contract.tariff_option if data.contract is not None else None
        ),
        available_fn=lambda data, _module: (
            data.contract is not None and bool(data.contract.tariff_option)
        ),
    ),
    LegrandSensorDescription(
        key="contract_power",
        translation_key="contract_power",
        value_fn=lambda data, _module: (
            data.contract.power_threshold if data.contract is not None else None
        ),
        available_fn=lambda data, _module: data.contract is not None,
        attributes_fn=lambda data, _module: (
            {
                "unit": data.contract.power_unit,
            }
            if data.contract is not None
            else None
        ),
    ),
    LegrandSensorDescription(
        key="peak_price",
        translation_key="peak_price",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=(f"{CURRENCY_EURO}/kWh"),
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
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=(f"{CURRENCY_EURO}/kWh"),
        suggested_display_precision=4,
        value_fn=lambda data, _module: (
            data.contract.off_peak_price if data.contract is not None else None
        ),
        available_fn=lambda data, _module: (
            data.contract is not None and data.contract.off_peak_price is not None
        ),
    ),
)


MODULE_SENSOR_DESCRIPTIONS: tuple[
    LegrandSensorDescription,
    ...,
] = (
    LegrandSensorDescription(
        key="circuit_energy_today",
        translation_key="circuit_energy_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=(UnitOfEnergy.KILO_WATT_HOUR),
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=3,
        module=True,
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
        available_fn=lambda data, module: (
            (
                measurements := _module_measurements(
                    data,
                    module,
                )
            )
            is not None
            and measurements.energy_today is not None
        ),
    ),
    LegrandSensorDescription(
        key="circuit_cost_today",
        translation_key="circuit_cost_today",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        module=True,
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
        available_fn=lambda data, module: (
            (
                measurements := _module_measurements(
                    data,
                    module,
                )
            )
            is not None
            and measurements.cost_today is not None
        ),
    ),
    LegrandSensorDescription(
        key="circuit_cost_peak_today",
        translation_key=("circuit_cost_peak_today"),
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        module=True,
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
            (
                measurements := _module_measurements(
                    data,
                    module,
                )
            )
            is not None
            and measurements.cost_peak_today is not None
        ),
    ),
    LegrandSensorDescription(
        key="circuit_cost_off_peak_today",
        translation_key=("circuit_cost_off_peak_today"),
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        module=True,
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
            (
                measurements := _module_measurements(
                    data,
                    module,
                )
            )
            is not None
            and measurements.cost_off_peak_today is not None
        ),
    ),
    LegrandSensorDescription(
        key="module_type",
        translation_key="module_type",
        module=True,
        entity_registry_enabled_default=False,
        value_fn=lambda _data, module: module.type,
        available_fn=lambda _data, module: bool(module.type),
    ),
    LegrandSensorDescription(
        key="room",
        translation_key="room",
        module=True,
        entity_registry_enabled_default=False,
        value_fn=lambda _data, module: module.room,
        available_fn=lambda _data, module: module.room is not None,
    ),
    LegrandSensorDescription(
        key="setup_date",
        translation_key="setup_date",
        device_class=SensorDeviceClass.TIMESTAMP,
        module=True,
        entity_registry_enabled_default=False,
        value_fn=lambda _data, module: (
            dt_util.utc_from_timestamp(module.setup_date)
            if module.setup_date is not None
            else None
        ),
        available_fn=lambda _data, module: module.setup_date is not None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: (AddConfigEntryEntitiesCallback),
) -> None:
    """Set up Legrand Energy sensors."""
    coordinator: LegrandEnergyCoordinator = entry.runtime_data

    main_module_id = get_main_module_id(coordinator)

    entities: list[LegrandSensor] = []

    if main_module_id is not None:
        entities.extend(
            LegrandSensor(
                coordinator=coordinator,
                module_id=main_module_id,
                description=description,
            )
            for description in GLOBAL_SENSOR_DESCRIPTIONS
        )

    for module_id, module in coordinator.data.modules.items():
        if module.bridge is None:
            continue

        entities.extend(
            LegrandSensor(
                coordinator=coordinator,
                module_id=module_id,
                description=description,
            )
            for description in MODULE_SENSOR_DESCRIPTIONS
        )

    async_add_entities(entities)


class LegrandSensor(
    LegrandEntity,
    SensorEntity,
):
    """Representation of a Legrand Energy sensor."""

    entity_description: LegrandSensorDescription

    def __init__(
        self,
        coordinator: LegrandEnergyCoordinator,
        module_id: str,
        description: LegrandSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            module_id,
        )

        self.entity_description = description

        self._attr_unique_id = f"{module_id}_{description.key}"

    @property
    def native_value(
        self,
    ) -> str | int | float | datetime | None:
        """Return the native sensor value."""
        module = self.module

        if module is None:
            return None

        return self.entity_description.value_fn(
            self.coordinator.data,
            module,
        )

    @property
    def available(self) -> bool:
        """Return whether the sensor is available."""
        if not super().available:
            return False

        module = self.module

        if module is None:
            return False

        return self.entity_description.available_fn(
            self.coordinator.data,
            module,
        )

    @property
    def extra_state_attributes(
        self,
    ) -> Mapping[str, Any] | None:
        """Return additional state attributes."""
        if self.entity_description.attributes_fn is None:
            return None

        module = self.module

        if module is None:
            return None

        return self.entity_description.attributes_fn(
            self.coordinator.data,
            module,
        )
