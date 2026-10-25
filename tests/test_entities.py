"""Tests for Legrand Energy entities and platforms."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.legrand_energy.binary_sensor import (
    LegrandBinarySensor,
)
from custom_components.legrand_energy.binary_sensor import (
    async_setup_entry as async_setup_binary_sensors,
)
from custom_components.legrand_energy.button import (
    LegrandRefreshButton,
)
from custom_components.legrand_energy.button import (
    async_setup_entry as async_setup_buttons,
)
from custom_components.legrand_energy.entity import LegrandEntity, get_main_module_id
from custom_components.legrand_energy.models import (
    FluidType,
    LegrandEnergyData,
    LegrandMeasurements,
    LegrandModule,
)
from custom_components.legrand_energy.sensor import (
    GLOBAL_SENSOR_DESCRIPTIONS,
    MODULE_SENSOR_DESCRIPTIONS,
    LegrandSensor,
)
from custom_components.legrand_energy.sensor import (
    async_setup_entry as async_setup_sensors,
)
from custom_components.legrand_energy.tariff_engine import TariffState


def _coordinator(hass, modules, *, tariff=None, measurements=None, by_module=None):
    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.config_entry.entry_id = "entry-id"
    coordinator.last_update_success = True
    coordinator.data = LegrandEnergyData(
        modules=modules,
        tariff=tariff,
        measurements=measurements,
        measurements_by_module=by_module or {},
    )
    return coordinator


def test_get_main_module_id_prefers_unsuffixed(hass) -> None:
    modules = {
        "main": LegrandModule(id="main", name="EcoMeter", type="NLE"),
        "main#0": LegrandModule(
            id="main#0",
            name="Circuit",
            type="NLE",
            bridge="main",
        ),
    }
    assert get_main_module_id(_coordinator(hass, modules)) == "main"


def test_get_main_module_id_fallback_and_none(hass) -> None:
    modules = {
        "bridge#physical": LegrandModule(
            id="bridge#physical",
            name="EcoMeter",
            type="NLE",
        ),
        "child": LegrandModule(
            id="child",
            name="Circuit",
            type="NLPC",
            bridge="bridge#physical",
        ),
    }
    assert get_main_module_id(_coordinator(hass, modules)) == "bridge#physical"
    assert get_main_module_id(_coordinator(hass, {})) is None


def test_entity_device_info_and_availability(hass) -> None:
    modules = {
        "main": LegrandModule(id="main", name="EcoMeter", type="NLE"),
        "main#0": LegrandModule(
            id="main#0",
            name="Circuit 1",
            type="NLE",
            bridge="main",
        ),
    }
    coordinator = _coordinator(hass, modules)

    with patch(
        "custom_components.legrand_energy.entity.dr.async_get_device_id_by_identifier",
        create=True,
        return_value="parent-device-id",
    ):
        main = LegrandEntity(coordinator, "main")
        child = LegrandEntity(coordinator, "main#0")

    assert main.device_info["model"] == "EcoMeter"
    assert "via_device_id" not in main.device_info
    assert child.device_info["model"] == "EcoMeter Circuit"
    assert child.device_info["via_device_id"] == "parent-device-id"
    assert child.module == modules["main#0"]
    assert child.available is True

    coordinator.data = LegrandEnergyData(modules={"main": modules["main"]})
    assert child.module is None
    assert child.available is False


@pytest.mark.asyncio
async def test_button_setup_and_press(hass) -> None:
    modules = {"main:1": LegrandModule(id="main:1", name="EcoMeter", type="NLE")}
    coordinator = _coordinator(hass, modules)
    coordinator.async_request_refresh = AsyncMock()
    entry = SimpleNamespace(runtime_data=coordinator)
    added = []

    await async_setup_buttons(hass, entry, added.extend)

    assert len(added) == 1
    button = added[0]
    assert isinstance(button, LegrandRefreshButton)
    assert button.unique_id == "legrand_energy_main_1_refresh"

    await button.async_press()
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_button_setup_without_main_module(hass) -> None:
    coordinator = _coordinator(hass, {})
    entry = SimpleNamespace(runtime_data=coordinator)
    added = []

    await async_setup_buttons(hass, entry, added.extend)

    assert added == []


@pytest.mark.asyncio
async def test_binary_sensor_setup_and_state(hass) -> None:
    module = LegrandModule(id="main", name="EcoMeter", type="NLE")
    tariff = MagicMock(spec=TariffState)
    tariff.is_off_peak = True
    coordinator = _coordinator(hass, {"main": module}, tariff=tariff)
    entry = SimpleNamespace(runtime_data=coordinator)
    added = []

    await async_setup_binary_sensors(
        hass, entry, lambda entities: added.extend(entities)
    )

    assert len(added) == 1
    entity = added[0]
    assert isinstance(entity, LegrandBinarySensor)
    assert entity.unique_id == "main_off_peak"
    assert entity.available is True
    assert entity.is_on is True

    coordinator.data = LegrandEnergyData(modules={"main": module})
    assert entity.available is False
    assert entity.is_on is None


@pytest.mark.asyncio
async def test_binary_sensor_setup_removes_obsolete_entities(hass) -> None:
    module = LegrandModule(id="main", name="EcoMeter", type="NLE")
    coordinator = _coordinator(hass, {"main": module})
    entry = SimpleNamespace(runtime_data=coordinator)
    registry = MagicMock()
    registry.async_get_entity_id.side_effect = ["binary_sensor.old_peak", None]

    with patch(
        "custom_components.legrand_energy.binary_sensor.er.async_get",
        return_value=registry,
    ):
        await async_setup_binary_sensors(hass, entry, lambda entities: list(entities))

    registry.async_remove.assert_called_once_with("binary_sensor.old_peak")


@pytest.mark.asyncio
async def test_sensor_setup_and_values(hass) -> None:
    main = LegrandModule(id="main", name="EcoMeter", type="NLE")
    circuit = LegrandModule(
        id="main#0",
        name="Circuit 1",
        type="NLE",
        bridge="main",
        fluid_type=FluidType.ELECTRICITY,
    )
    global_measurements = LegrandMeasurements(energy_today=3.2)
    module_measurements = LegrandMeasurements(energy_today=1.1)
    coordinator = _coordinator(
        hass,
        {"main": main, "main#0": circuit},
        measurements=global_measurements,
        by_module={"main#0": module_measurements},
    )
    entry = SimpleNamespace(runtime_data=coordinator)
    added = []

    with patch(
        "custom_components.legrand_energy.entity.dr.async_get_device_id_by_identifier",
        create=True,
        return_value="parent-device-id",
    ):
        await async_setup_sensors(hass, entry, added.extend)

    assert len(added) == len(GLOBAL_SENSOR_DESCRIPTIONS) + len(
        MODULE_SENSOR_DESCRIPTIONS
    )

    global_sensor = next(
        entity for entity in added if entity.unique_id == "main_energy_today"
    )
    module_sensor = next(
        entity for entity in added if entity.unique_id == "main#0_circuit_energy_today"
    )

    assert isinstance(global_sensor, LegrandSensor)
    assert global_sensor.native_value == 3.2
    assert global_sensor.available is True
    assert module_sensor.native_value == 1.1
    assert module_sensor.available is True

    coordinator.data = LegrandEnergyData(
        modules={"main": main, "main#0": circuit},
        measurements=LegrandMeasurements(),
        measurements_by_module={"main#0": LegrandMeasurements()},
    )
    assert global_sensor.available is False
    assert module_sensor.available is False


def test_sensor_optional_attributes(hass) -> None:
    module = LegrandModule(id="main", name="EcoMeter", type="NLE")
    coordinator = _coordinator(
        hass,
        {"main": module},
        measurements=LegrandMeasurements(energy_today=1.0),
    )
    description = GLOBAL_SENSOR_DESCRIPTIONS[0]
    sensor = LegrandSensor(coordinator, "main", description)

    assert sensor.extra_state_attributes is None
    assert sensor.last_reset is not None
