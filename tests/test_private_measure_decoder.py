"""Tests for private measure decoder."""

import pytest

from custom_components.legrand_energy.helpers.private_measure_decoder import (
    decode_energy_points,
    decode_energy_points_by_module,
)


def test_decode_energy_points() -> None:
    """Decode split energy and price channels."""
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
    """Group modules separately and sort their points chronologically."""
    data = {
        "body": {
            "home": {
                "modules": [
                    {
                        "id": "module-1",
                        "measures": [
                            {
                                "beg_time": 2000,
                                "step_time": 300,
                                "value": [[100, None, None, None]],
                            },
                            {
                                "beg_time": 1000,
                                "step_time": 300,
                                "value": [[50, None, None, None]],
                            },
                        ],
                    },
                    {
                        "id": "module-2",
                        "measures": [
                            {
                                "beg_time": 1500,
                                "step_time": 300,
                                "value": [[25, None, None, None]],
                            }
                        ],
                    },
                ]
            }
        }
    }

    points_by_module = decode_energy_points_by_module(data)

    assert list(points_by_module) == ["module-1", "module-2"]
    assert [point.energy for point in points_by_module["module-1"]] == [50, 100]
    assert [point.energy for point in points_by_module["module-2"]] == [25]


def test_ignore_invalid_rows_and_boolean_values() -> None:
    """Ignore malformed rows and booleans masquerading as integers."""
    data = {
        "body": {
            "home": {
                "modules": [
                    {
                        "id": "module",
                        "measures": [
                            {
                                "beg_time": 1783350000,
                                "step_time": 300,
                                "value": [
                                    "invalid",
                                    [True, None, None, None],
                                    [None, False, None, None],
                                    [125, None, None, None],
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
    assert points[0].energy == 125


def test_invalid_response_returns_no_points() -> None:
    """Return an empty result for incomplete responses."""
    assert decode_energy_points({}) == []
    assert decode_energy_points({"body": {}}) == []
    assert decode_energy_points({"body": {"home": {}}}) == []
