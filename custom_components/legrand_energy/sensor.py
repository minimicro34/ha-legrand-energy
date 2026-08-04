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
from homeassistant.const import (
    CURRENCY_EURO,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import LegrandEnergyCoordinator
from .entity import LegrandEntity, get_main_module_id
from .models import (
    FluidMeasurements,
    FluidType,
    LegrandEnergyData,
    LegrandMeasurements,
    LegrandModule,
)

SensorValue = str | int | float | datetime | None
ValueFn = Callable[[LegrandEnergyData, LegrandModule | None], SensorValue]
AvailableFn = Callable[[LegrandEnergyData, LegrandModule | None], bool]
AttributesFn = Callable[
    [LegrandEnergyData, LegrandModule | None],
    dict[str, Any] | None,
]
LastResetFn = Callable[
    [LegrandEnergyData, LegrandModule | None],
    datetime | None,
]


@dataclass(frozen=True, kw_only=True)
class LegrandSensorDescription(SensorEntityDescription):
    """Describe a Legrand Energy sensor."""

    value_fn: ValueFn
    available_fn: AvailableFn = lambda _data, _module: True
    attributes_fn: AttributesFn | None = None
    last_reset_fn: LastResetFn | None = None


def _start_of_today() -> datetime:
    """Return the start of the current local day."""
    now = dt_util.now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _start_of_week() -> datetime:
    """Return the start of the current local week."""
    today = _start_of_today()
    return today - timedelta(days=today.weekday())


def _start_of_month() -> datetime:
    """Return the start of the current local month."""
    return _start_of_today().replace(day=1)


def _start_of_year() -> datetime:
    """Return the start of the current local year."""
    return _start_of_today().replace(month=1, day=1)


def _format_remaining(remaining: timedelta | None) -> str | None:
    """Format a remaining duration."""
    if remaining is None:
        return None
    total_seconds = max(0, int(remaining.total_seconds()))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours} h {minutes:02d} min" if hours > 0 else f"{minutes} min"


def _remaining_until(target: datetime | None) -> timedelta | None:
    """Return remaining time until a target datetime."""
    if target is None:
        return None
    return target - dt_util.now()


def _module_measurements(
    data: LegrandEnergyData,
    module: LegrandModule | None,
) -> LegrandMeasurements | FluidMeasurements | None:
    """Return measurements for a module."""
    if module is None:
        return None

    return data.module_measurements(module)


def _global_measurement_description(
    *,
    key: str,
    translation_key: str,
    field: str,
    device_class: SensorDeviceClass,
    unit: str,
    state_class: SensorStateClass,
    precision: int,
    last_reset_fn: LastResetFn | None = None,
) -> LegrandSensorDescription:
    """Build a global measurement sensor description."""

    def value_fn(
        data: LegrandEnergyData,
        _module: LegrandModule | None,
    ) -> SensorValue:
        measurements = data.measurements
        return getattr(measurements, field) if measurements is not None else None

    def available_fn(
        data: LegrandEnergyData,
        _module: LegrandModule | None,
    ) -> bool:
        measurements = data.measurements
        return measurements is not None and getattr(measurements, field) is not None

    return LegrandSensorDescription(
        key=key,
        translation_key=translation_key,
        device_class=device_class,
        native_unit_of_measurement=unit,
        state_class=state_class,
        suggested_display_precision=precision,
        value_fn=value_fn,
        available_fn=available_fn,
        last_reset_fn=last_reset_fn,
    )


def _module_measurement_description(
    *,
    key: str,
    translation_key: str,
    field: str,
    device_class: SensorDeviceClass,
    unit: str,
    state_class: SensorStateClass,
    precision: int,
    last_reset_fn: LastResetFn | None = None,
) -> LegrandSensorDescription:
    """Build a per-module measurement sensor description."""

    def value_fn(
        data: LegrandEnergyData,
        module: LegrandModule | None,
    ) -> SensorValue:
        measurements = _module_measurements(data, module)
        return getattr(measurements, field) if measurements is not None else None

    def available_fn(
        data: LegrandEnergyData,
        module: LegrandModule | None,
    ) -> bool:
        measurements = _module_measurements(data, module)
        return measurements is not None and getattr(measurements, field) is not None

    return LegrandSensorDescription(
        key=key,
        translation_key=translation_key,
        device_class=device_class,
        native_unit_of_measurement=unit,
        state_class=state_class,
        suggested_display_precision=precision,
        value_fn=value_fn,
        available_fn=available_fn,
        last_reset_fn=last_reset_fn,
    )


GLOBAL_SENSOR_DESCRIPTIONS: tuple[LegrandSensorDescription, ...] = (
    _global_measurement_description(
        key="energy_today",
        translation_key="energy_today",
        field="energy_today",
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        precision=3,
        last_reset_fn=lambda _data, _module: _start_of_today(),
    ),
    _global_measurement_description(
        key="energy_peak_today",
        translation_key="energy_peak_today",
        field="energy_peak_today",
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        precision=3,
        last_reset_fn=lambda _data, _module: _start_of_today(),
    ),
    _global_measurement_description(
        key="energy_off_peak_today",
        translation_key="energy_off_peak_today",
        field="energy_off_peak_today",
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        precision=3,
        last_reset_fn=lambda _data, _module: _start_of_today(),
    ),
    LegrandSensorDescription(
        key="projected_energy_today",
        translation_key="projected_energy_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
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
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
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
        key="projected_energy_year",
        translation_key="projected_energy_year",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=3,
        value_fn=lambda data, _module: (
            data.projections.energy_end_of_year
            if data.projections is not None
            else None
        ),
        available_fn=lambda data, _module: (
            data.projections is not None
            and data.projections.energy_end_of_year is not None
        ),
    ),
    _global_measurement_description(
        key="energy_week",
        translation_key="energy_week",
        field="energy_week",
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        precision=3,
        last_reset_fn=lambda _data, _module: _start_of_week(),
    ),
    _global_measurement_description(
        key="energy_month",
        translation_key="energy_month",
        field="energy_month",
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        precision=3,
        last_reset_fn=lambda _data, _module: _start_of_month(),
    ),
    _global_measurement_description(
        key="energy_year",
        translation_key="energy_year",
        field="energy_year",
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        precision=3,
        last_reset_fn=lambda _data, _module: _start_of_year(),
    ),
    _global_measurement_description(
        key="cost_today",
        translation_key="cost_today",
        field="cost_today",
        device_class=SensorDeviceClass.MONETARY,
        unit=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        precision=2,
        last_reset_fn=lambda _data, _module: _start_of_today(),
    ),
    _global_measurement_description(
        key="cost_peak_today",
        translation_key="cost_peak_today",
        field="cost_peak_today",
        device_class=SensorDeviceClass.MONETARY,
        unit=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        precision=2,
        last_reset_fn=lambda _data, _module: _start_of_today(),
    ),
    _global_measurement_description(
        key="cost_off_peak_today",
        translation_key="cost_off_peak_today",
        field="cost_off_peak_today",
        device_class=SensorDeviceClass.MONETARY,
        unit=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        precision=2,
        last_reset_fn=lambda _data, _module: _start_of_today(),
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
        key="projected_cost_year",
        translation_key="projected_cost_year",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda data, _module: (
            data.projections.cost_end_of_year if data.projections is not None else None
        ),
        available_fn=lambda data, _module: (
            data.projections is not None
            and data.projections.cost_end_of_year is not None
        ),
    ),
    _global_measurement_description(
        key="cost_week",
        translation_key="cost_week",
        field="cost_week",
        device_class=SensorDeviceClass.MONETARY,
        unit=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        precision=2,
        last_reset_fn=lambda _data, _module: _start_of_week(),
    ),
    _global_measurement_description(
        key="cost_month",
        translation_key="cost_month",
        field="cost_month",
        device_class=SensorDeviceClass.MONETARY,
        unit=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        precision=2,
        last_reset_fn=lambda _data, _module: _start_of_month(),
    ),
    _global_measurement_description(
        key="cost_year",
        translation_key="cost_year",
        field="cost_year",
        device_class=SensorDeviceClass.MONETARY,
        unit=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        precision=2,
        last_reset_fn=lambda _data, _module: _start_of_year(),
    ),
    _global_measurement_description(
        key="power",
        translation_key="power",
        field="power",
        device_class=SensorDeviceClass.POWER,
        unit=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        precision=0,
    ),
    LegrandSensorDescription(
        key="contract_option",
        translation_key="contract_option",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _module: (
            {
                "peak_and_off_peak": "HP/HC",
                "base": "Base",
            }.get(
                data.contract.tariff_option,
                data.contract.tariff_option,
            )
            if data.contract is not None
            else None
        ),
        available_fn=lambda data, _module: (
            data.contract is not None and bool(data.contract.tariff_option)
        ),
    ),
    LegrandSensorDescription(
        key="off_peak_price",
        translation_key="off_peak_price",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=f"{CURRENCY_EURO}/kWh",
        suggested_display_precision=4,
        value_fn=lambda data, _module: (
            data.contract.off_peak_price if data.contract is not None else None
        ),
        available_fn=lambda data, _module: (
            data.contract is not None and data.contract.off_peak_price is not None
        ),
    ),
    LegrandSensorDescription(
        key="peak_price",
        translation_key="peak_price",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.MONETARY,
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
        key="contract_power",
        translation_key="contract_power",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="kVA",
        suggested_display_precision=0,
        value_fn=lambda data, _module: (
            data.contract.power_threshold if data.contract is not None else None
        ),
        available_fn=lambda data, _module: (
            data.contract is not None and data.contract.power_threshold is not None
        ),
    ),
    LegrandSensorDescription(
        key="contract_tariff",
        translation_key="contract_tariff",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _module: (
            {"custom": "Personnalisé"}.get(
                data.contract.tariff,
                data.contract.tariff,
            )
            if data.contract is not None
            else None
        ),
        available_fn=lambda data, _module: (
            data.contract is not None and bool(data.contract.tariff)
        ),
    ),
    LegrandSensorDescription(
        key="current_tariff",
        translation_key="current_tariff",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _module: (
            {"peak": "HP", "off_peak": "HC"}.get(
                data.tariff.price_type,
                data.tariff.price_type,
            )
            if data.tariff is not None
            else None
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
            else {}
        ),
    ),
    LegrandSensorDescription(
        key="current_price",
        translation_key="current_price",
        device_class=SensorDeviceClass.MONETARY,
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
    LegrandSensorDescription(
        key="contract_type",
        translation_key="contract_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _module: (
            {"electricity": "Électricité"}.get(data.contract.type, data.contract.type)
            if data.contract is not None
            else None
        ),
        available_fn=lambda data, _module: (
            data.contract is not None and bool(data.contract.type)
        ),
    ),
    LegrandSensorDescription(
        key="module_type",
        translation_key="module_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda _data, module: module.type if module is not None else None,
        available_fn=lambda _data, module: module is not None and bool(module.type),
    ),
    LegrandSensorDescription(
        key="room",
        translation_key="room",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda _data, module: module.room if module is not None else None,
        available_fn=lambda _data, module: (
            module is not None and module.room is not None
        ),
    ),
    LegrandSensorDescription(
        key="setup_date",
        translation_key="setup_date",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
        value_fn=lambda _data, module: (
            dt_util.utc_from_timestamp(module.setup_date)
            if module is not None and module.setup_date is not None
            else None
        ),
        available_fn=lambda _data, module: (
            module is not None and module.setup_date is not None
        ),
    ),
)


MODULE_SENSOR_DESCRIPTIONS: tuple[LegrandSensorDescription, ...] = (
    _module_measurement_description(
        key="circuit_energy_today",
        translation_key="circuit_energy_today",
        field="energy_today",
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        precision=3,
        last_reset_fn=lambda _data, _module: _start_of_today(),
    ),
    _module_measurement_description(
        key="circuit_energy_peak_today",
        translation_key="circuit_energy_peak_today",
        field="energy_peak_today",
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        precision=3,
        last_reset_fn=lambda _data, _module: _start_of_today(),
    ),
    _module_measurement_description(
        key="circuit_energy_off_peak_today",
        translation_key="circuit_energy_off_peak_today",
        field="energy_off_peak_today",
        device_class=SensorDeviceClass.ENERGY,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        precision=3,
        last_reset_fn=lambda _data, _module: _start_of_today(),
    ),
    _module_measurement_description(
        key="circuit_cost_today",
        translation_key="circuit_cost_today",
        field="cost_today",
        device_class=SensorDeviceClass.MONETARY,
        unit=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        precision=2,
        last_reset_fn=lambda _data, _module: _start_of_today(),
    ),
    _module_measurement_description(
        key="circuit_cost_peak_today",
        translation_key="circuit_cost_peak_today",
        field="cost_peak_today",
        device_class=SensorDeviceClass.MONETARY,
        unit=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        precision=2,
        last_reset_fn=lambda _data, _module: _start_of_today(),
    ),
    _module_measurement_description(
        key="circuit_cost_off_peak_today",
        translation_key="circuit_cost_off_peak_today",
        field="cost_off_peak_today",
        device_class=SensorDeviceClass.MONETARY,
        unit=CURRENCY_EURO,
        state_class=SensorStateClass.TOTAL,
        precision=2,
        last_reset_fn=lambda _data, _module: _start_of_today(),
    ),
    LegrandSensorDescription(
        key="module_type",
        translation_key="module_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda _data, module: module.type if module is not None else None,
        available_fn=lambda _data, module: module is not None and bool(module.type),
    ),
    LegrandSensorDescription(
        key="room",
        translation_key="room",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda _data, module: module.room if module is not None else None,
        available_fn=lambda _data, module: (
            module is not None and module.room is not None
        ),
    ),
    LegrandSensorDescription(
        key="setup_date",
        translation_key="setup_date",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
        value_fn=lambda _data, module: (
            dt_util.utc_from_timestamp(module.setup_date)
            if module is not None and module.setup_date is not None
            else None
        ),
        available_fn=lambda _data, module: (
            module is not None and module.setup_date is not None
        ),
    ),
)


MODULE_DIAGNOSTIC_SENSOR_DESCRIPTIONS: tuple[LegrandSensorDescription, ...] = (
    LegrandSensorDescription(
        key="module_type",
        translation_key="module_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda _data, module: module.type if module is not None else None,
        available_fn=lambda _data, module: module is not None and bool(module.type),
    ),
    LegrandSensorDescription(
        key="room",
        translation_key="room",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda _data, module: module.room if module is not None else None,
        available_fn=lambda _data, module: (
            module is not None and module.room is not None
        ),
    ),
    LegrandSensorDescription(
        key="setup_date",
        translation_key="setup_date",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
        value_fn=lambda _data, module: (
            dt_util.utc_from_timestamp(module.setup_date)
            if module is not None and module.setup_date is not None
            else None
        ),
        available_fn=lambda _data, module: (
            module is not None and module.setup_date is not None
        ),
    ),
)


def _fluid_sensor_descriptions(
    *,
    prefix: str,
    device_class: SensorDeviceClass,
    unit: str,
) -> tuple[LegrandSensorDescription, ...]:
    """Build fluid consumption and cost sensor descriptions."""
    return (
        _module_measurement_description(
            key=f"{prefix}_consumption_today",
            translation_key=f"{prefix}_consumption_today",
            field="consumption_today",
            device_class=device_class,
            unit=unit,
            state_class=SensorStateClass.TOTAL,
            precision=3,
            last_reset_fn=lambda _data, _module: _start_of_today(),
        ),
        _module_measurement_description(
            key=f"{prefix}_consumption_week",
            translation_key=f"{prefix}_consumption_week",
            field="consumption_week",
            device_class=device_class,
            unit=unit,
            state_class=SensorStateClass.TOTAL,
            precision=3,
            last_reset_fn=lambda _data, _module: _start_of_week(),
        ),
        _module_measurement_description(
            key=f"{prefix}_consumption_month",
            translation_key=f"{prefix}_consumption_month",
            field="consumption_month",
            device_class=device_class,
            unit=unit,
            state_class=SensorStateClass.TOTAL,
            precision=3,
            last_reset_fn=lambda _data, _module: _start_of_month(),
        ),
        _module_measurement_description(
            key=f"{prefix}_consumption_year",
            translation_key=f"{prefix}_consumption_year",
            field="consumption_year",
            device_class=device_class,
            unit=unit,
            state_class=SensorStateClass.TOTAL,
            precision=3,
            last_reset_fn=lambda _data, _module: _start_of_year(),
        ),
        _module_measurement_description(
            key=f"{prefix}_cost_today",
            translation_key=f"{prefix}_cost_today",
            field="cost_today",
            device_class=SensorDeviceClass.MONETARY,
            unit=CURRENCY_EURO,
            state_class=SensorStateClass.TOTAL,
            precision=2,
            last_reset_fn=lambda _data, _module: _start_of_today(),
        ),
        _module_measurement_description(
            key=f"{prefix}_cost_week",
            translation_key=f"{prefix}_cost_week",
            field="cost_week",
            device_class=SensorDeviceClass.MONETARY,
            unit=CURRENCY_EURO,
            state_class=SensorStateClass.TOTAL,
            precision=2,
            last_reset_fn=lambda _data, _module: _start_of_week(),
        ),
        _module_measurement_description(
            key=f"{prefix}_cost_month",
            translation_key=f"{prefix}_cost_month",
            field="cost_month",
            device_class=SensorDeviceClass.MONETARY,
            unit=CURRENCY_EURO,
            state_class=SensorStateClass.TOTAL,
            precision=2,
            last_reset_fn=lambda _data, _module: _start_of_month(),
        ),
        _module_measurement_description(
            key=f"{prefix}_cost_year",
            translation_key=f"{prefix}_cost_year",
            field="cost_year",
            device_class=SensorDeviceClass.MONETARY,
            unit=CURRENCY_EURO,
            state_class=SensorStateClass.TOTAL,
            precision=2,
            last_reset_fn=lambda _data, _module: _start_of_year(),
        ),
    )


WATER_SENSOR_DESCRIPTIONS = _fluid_sensor_descriptions(
    prefix="water",
    device_class=SensorDeviceClass.WATER,
    unit=UnitOfVolume.LITERS,
)

# Home Control reports gas in dm³. One dm³ is exactly one litre, and Home
# Assistant's gas device class supports litres rather than a distinct dm³ unit.
GAS_SENSOR_DESCRIPTIONS = _fluid_sensor_descriptions(
    prefix="gas",
    device_class=SensorDeviceClass.GAS,
    unit=UnitOfVolume.LITERS,
)


def _descriptions_for_module(
    data: LegrandEnergyData,
    module: LegrandModule,
) -> tuple[LegrandSensorDescription, ...]:
    """Return sensor descriptions supported by a module."""
    if module.fluid_type is FluidType.ELECTRICITY:
        return MODULE_SENSOR_DESCRIPTIONS

    measurements = data.module_measurements(module)

    if module.fluid_type is FluidType.WATER:
        descriptions = WATER_SENSOR_DESCRIPTIONS
    else:
        descriptions = GAS_SENSOR_DESCRIPTIONS

    if isinstance(measurements, FluidMeasurements):
        has_cost = any(
            value is not None
            for value in (
                measurements.cost_today,
                measurements.cost_week,
                measurements.cost_month,
                measurements.cost_year,
            )
        )

        if not has_cost:
            descriptions = tuple(
                description
                for description in descriptions
                if "_cost_" not in description.key
            )

    return descriptions + MODULE_DIAGNOSTIC_SENSOR_DESCRIPTIONS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
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
            for description in _descriptions_for_module(
                coordinator.data,
                module,
            )
        )

    async_add_entities(entities)


class LegrandSensor(LegrandEntity, SensorEntity):
    """Representation of a Legrand Energy sensor."""

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
        """Return the native sensor value."""
        return self.entity_description.value_fn(
            self.coordinator.data,
            self.module,
        )

    @property
    def available(self) -> bool:
        """Return whether the sensor is available."""
        return super().available and self.entity_description.available_fn(
            self.coordinator.data,
            self.module,
        )

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return additional state attributes."""
        attributes_fn = self.entity_description.attributes_fn
        if attributes_fn is None:
            return None
        return attributes_fn(self.coordinator.data, self.module)

    @property
    def last_reset(self) -> datetime | None:
        """Return the beginning of the sensor accumulation period."""
        last_reset_fn = self.entity_description.last_reset_fn

        if last_reset_fn is None:
            return None

        return last_reset_fn(
            self.coordinator.data,
            self.module,
        )
