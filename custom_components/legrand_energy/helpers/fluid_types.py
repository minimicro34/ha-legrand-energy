"""Private measurement definitions for supported fluid types."""

from __future__ import annotations

from ..models.fluid import FluidType

PRIVATE_MEASURE_TYPE_ELECTRICITY = (
    "sum_energy_elec,"
    "sum_energy_elec$0,"
    "sum_energy_elec$1,"
    "sum_energy_elec$2,"
    "sum_energy_price$0,"
    "sum_energy_price$1,"
    "sum_energy_price$2"
)

PRIVATE_MEASURE_TYPE_FLUID = "sum_fluid_consumption$0,sum_fluid_price$0"


def private_measure_type(fluid_type: FluidType) -> str:
    """Return the private API measurement fields for a fluid type."""
    if fluid_type is FluidType.ELECTRICITY:
        return PRIVATE_MEASURE_TYPE_ELECTRICITY

    return PRIVATE_MEASURE_TYPE_FLUID
