"""Tests for fluid measurement definitions."""

import pytest

from custom_components.legrand_energy.helpers.fluid_types import (
    PRIVATE_MEASURE_TYPE_ELECTRICITY,
    PRIVATE_MEASURE_TYPE_FLUID,
    private_measure_type,
)
from custom_components.legrand_energy.models import FluidType


@pytest.mark.parametrize(
    ("fluid_type", "expected"),
    [
        (FluidType.ELECTRICITY, PRIVATE_MEASURE_TYPE_ELECTRICITY),
        (FluidType.WATER, PRIVATE_MEASURE_TYPE_FLUID),
        (FluidType.GAS, PRIVATE_MEASURE_TYPE_FLUID),
    ],
)
def test_private_measure_type(
    fluid_type: FluidType,
    expected: str,
) -> None:
    """Return the correct private API measurement fields."""
    assert private_measure_type(fluid_type) == expected
