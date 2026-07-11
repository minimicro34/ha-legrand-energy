"""Tests for private measure decoder."""

from custom_components.legrand_energy.helpers.private_measure_decoder import (
    decode_energy_points,
)


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
