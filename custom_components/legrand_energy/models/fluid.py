"""Fluid models for Legrand Energy."""

from enum import StrEnum


class FluidType(StrEnum):
    """Supported measurement fluid types."""

    ELECTRICITY = "electricity"
    WATER = "water"
    GAS = "gas"
