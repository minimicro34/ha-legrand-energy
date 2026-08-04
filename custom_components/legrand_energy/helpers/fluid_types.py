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


def detect_fluid_type(
    module_id: str,
    module_name: str,
) -> FluidType:
    """Detect the fluid type exposed by a Legrand module."""
    normalized = module_name.casefold()

    if module_id.endswith("#6") or "gaz" in normalized or "gas" in normalized:
        return FluidType.GAS

    if (
        module_id.endswith("#7")
        or module_id.endswith("#8")
        or "eau" in normalized
        or "water" in normalized
    ):
        return FluidType.WATER

    return FluidType.ELECTRICITY
