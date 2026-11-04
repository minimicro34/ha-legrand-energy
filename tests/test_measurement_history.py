"""Tests for chart-safe serialization of Netatmo energy points."""

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.legrand_energy.helpers.energy_series import EnergyPoint
from custom_components.legrand_energy.helpers.measurement_history import (
    serialize_energy_history,
)

START = datetime(2026, 11, 4, tzinfo=UTC)


def point(minutes: int, wh: float, step: int = 1500) -> EnergyPoint:
    return EnergyPoint(
        timestamp=START + timedelta(minutes=minutes),
        energy=wh,
        price=None,
        interval_seconds=step,
        tariff=None,
        zone_id=None,
    )


def test_uses_real_intervals_and_wh_to_kwh() -> None:
    result = serialize_energy_history(
        [point(50, 250, 300), point(0, 500, 1500)],
        start=START,
        end=START + timedelta(hours=2),
    )
    assert [row["energy_kwh"] for row in result] == [0.5, 0.25]
    assert [row["interval_seconds"] for row in result] == [1500, 300]
    assert len(result) == 2  # No invented data for the missing interval.


def test_half_open_window() -> None:
    assert (
        len(
            serialize_energy_history(
                [point(0, 100), point(60, 200)],
                start=START,
                end=START + timedelta(hours=1),
            )
        )
        == 1
    )


def test_rejects_unbounded_result() -> None:
    with pytest.raises(ValueError, match="maximum"):
        serialize_energy_history(
            [point(0, 100), point(1, 100)],
            start=START,
            end=START + timedelta(hours=1),
            limit=1,
        )


def test_rejects_naive_boundary() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        serialize_energy_history(
            [point(0, 100)],
            start=datetime(2026, 11, 4),
            end=START + timedelta(hours=1),
        )


def test_ignores_invalid_intervals() -> None:
    assert (
        serialize_energy_history(
            [point(0, 100, 0), point(25, -1)],
            start=START,
            end=START + timedelta(hours=1),
        )
        == []
    )


def test_preserves_dst_offsets_without_filling_missing_intervals() -> None:
    """Fall-back hour contains two distinct local 02:30 instants."""
    from zoneinfo import ZoneInfo

    paris = ZoneInfo("Europe/Paris")
    first = datetime(2026, 10, 25, 2, 30, tzinfo=paris, fold=0)
    second = datetime(2026, 10, 25, 2, 30, tzinfo=paris, fold=1)
    points = [
        EnergyPoint(
            timestamp=instant,
            energy=125,
            price=None,
            interval_seconds=1500,
            tariff=None,
            zone_id=None,
        )
        for instant in (first, second)
    ]
    result = serialize_energy_history(
        points,
        start=datetime(2026, 10, 25, 0, tzinfo=UTC),
        end=datetime(2026, 10, 26, 0, tzinfo=UTC),
    )
    assert len(result) == 2
    assert {row["timestamp"][-6:] for row in result} == {"+02:00", "+01:00"}
    assert sum(row["energy_kwh"] for row in result) == pytest.approx(0.25)


def test_rejects_reversed_history_window() -> None:
    with pytest.raises(ValueError, match="after start"):
        serialize_energy_history([point(0, 100)], start=START, end=START)
