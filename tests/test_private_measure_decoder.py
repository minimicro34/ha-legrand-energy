"""Tests for private measure decoder."""

import pytest

from custom_components.legrand_energy.helpers.private_measure_decoder import (
    decode_energy_points,
    decode_energy_points_by_module,
    decode_points_by_module,
)
from custom_components.legrand_energy.models import FluidType


def test_decode_energy_points() -> None:
    data = {
        "body": {
            "home": {
                "modules": [
                    {
                        "id": "00:04:74:12:24:d4#5",
                        "measures": [
                            {
                                "beg_time": 1783350000,
                                "step_time": 1500,
                                "value": [
                                    [None, None, 598, None, None, 0.1291, None],
                                    [None, None, None, 108, None, None, 0.0155],
                                ],
                            }
                        ],
                    }
                ]
            }
        }
    }

    points = decode_energy_points(data)

    assert len(points) == 2
    assert points[0].energy == 598
    assert points[0].price == 0.1291
    assert points[1].energy == 108
    assert points[1].price == 0.0155


def test_prefers_total_energy_value() -> None:
    """Prefer sum_energy_elec when the total value is available."""
    data = {
        "body": {
            "home": {
                "modules": [
                    {
                        "id": "total",
                        "measures": [
                            {
                                "beg_time": 1783350000,
                                "step_time": 300,
                                "value": [
                                    [900, 100, 200, 300, 0.1, 0.2, 0.3],
                                ],
                            }
                        ],
                    }
                ]
            }
        }
    }

    points = decode_energy_points(data)

    assert len(points) == 1
    assert points[0].energy == 900
    assert points[0].price == pytest.approx(0.6)


def test_decode_multiple_modules_and_sort_points() -> None:
    """Decode every module and sort points by timestamp."""
    data = {
        "body": {
            "home": {
                "modules": [
                    {
                        "id": "module-1",
                        "measures": [
                            {
                                "beg_time": 1783350300,
                                "step_time": 300,
                                "value": [
                                    [None, 20, None, None, 0.2, None, None],
                                ],
                            },
                            {
                                "beg_time": 1783350000,
                                "step_time": 300,
                                "value": [
                                    [None, 10, None, None, 0.1, None, None],
                                ],
                            },
                        ],
                    },
                    {
                        "id": "module-2",
                        "measures": [
                            {
                                "beg_time": 1783350000,
                                "step_time": 300,
                                "value": [
                                    [None, 30, None, None, 0.3, None, None],
                                ],
                            }
                        ],
                    },
                ]
            }
        }
    }

    points_by_module = decode_energy_points_by_module(data)

    assert list(points_by_module) == ["module-1", "module-2"]
    assert [point.energy for point in points_by_module["module-1"]] == [10, 20]
    assert [point.energy for point in points_by_module["module-2"]] == [30]


def test_ignore_invalid_rows_and_values() -> None:
    """Ignore malformed rows and non-numeric values."""
    data = {
        "body": {
            "home": {
                "modules": [
                    {
                        "id": "module-1",
                        "measures": [
                            {
                                "beg_time": 1783350000,
                                "step_time": 300,
                                "value": [
                                    "invalid",
                                    [None, None, None, None],
                                    [None, True, None, None, False],
                                    [None, "10", None, None, "0.2"],
                                    [None, 50, None, None, 0.5],
                                ],
                            }
                        ],
                    }
                ]
            }
        }
    }

    points = decode_energy_points(data)

    assert len(points) == 1
    assert points[0].energy == 50
    assert points[0].price == 0.5


def test_returns_empty_for_invalid_payload() -> None:
    """Return no points for malformed response structures."""
    assert decode_energy_points({}) == []
    assert decode_energy_points({"body": []}) == []
    assert decode_energy_points({"body": {"home": []}}) == []
    assert decode_energy_points({"body": {"home": {"modules": {}}}}) == []


def test_decode_water_measurements() -> None:
    """Decode water consumption and price values."""
    data = {
        "body": {
            "home": {
                "modules": [
                    {
                        "id": "bridge#8",
                        "measures": [
                            {
                                "beg_time": 1783350000,
                                "step_time": 300,
                                "value": [
                                    [125.5, 0.42],
                                    [20.0, None],
                                ],
                            }
                        ],
                    }
                ]
            }
        }
    }

    points_by_module = decode_points_by_module(
        data,
        fluid_type=FluidType.WATER,
    )

    points = points_by_module["bridge#8"]

    assert len(points) == 2
    assert points[0].energy == 125.5
    assert points[0].price == 0.42
    assert points[1].energy == 20.0
    assert points[1].price is None


def test_decode_gas_measurements() -> None:
    """Decode gas consumption and price values."""
    data = {
        "body": {
            "home": {
                "modules": [
                    {
                        "id": "bridge#6",
                        "measures": [
                            {
                                "beg_time": 1783350000,
                                "step_time": 300,
                                "value": [
                                    [750.0, 1.25],
                                ],
                            }
                        ],
                    }
                ]
            }
        }
    }

    points_by_module = decode_points_by_module(
        data,
        fluid_type=FluidType.GAS,
    )

    points = points_by_module["bridge#6"]

    assert len(points) == 1
    assert points[0].energy == 750.0
    assert points[0].price == 1.25
