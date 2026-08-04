"""Tests for fluid type helpers."""

import pytest

from custom_components.legrand_energy.helpers.fluid_types import detect_fluid_type
from custom_components.legrand_energy.models import FluidType


@pytest.mark.parametrize(
    ("module_id", "module_name", "expected"),
    [
        ("bridge#0", "Chauffe Eau", FluidType.ELECTRICITY),
        ("bridge#5", "Total", FluidType.ELECTRICITY),
        ("bridge#6", "Gaz", FluidType.GAS),
        ("bridge#7", "Eau chaude", FluidType.WATER),
        ("bridge#8", "Eau froide", FluidType.WATER),
        ("other", "Gaz", FluidType.GAS),
        ("other", "Eau jardin", FluidType.WATER),
        ("other", "Water garden", FluidType.WATER),
    ],
)
def test_detect_fluid_type(
    module_id: str,
    module_name: str,
    expected: FluidType,
) -> None:
    """Detect the fluid type from module metadata."""
    assert detect_fluid_type(module_id, module_name) is expected
