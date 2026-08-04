"""Tests for energy models."""

from custom_components.legrand_energy.models import (
    FluidMeasurements,
    FluidType,
    LegrandEnergyData,
    LegrandModule,
)


def test_module_measurements() -> None:
    module = LegrandModule(
        id="water",
        name="Water",
        type="NWM",
        fluid_type=FluidType.WATER,
    )

    water = FluidMeasurements(consumption_today=123)

    data = LegrandEnergyData(
        modules={"water": module},
        water_measurements_by_module={"water": water},
    )

    assert data.module_measurements(module) is water
