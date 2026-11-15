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


def test_daily_totals_do_not_claim_a_single_hp_hc_tariff() -> None:
    daily = point(0, 18000, 86400)
    daily.tariff = "HP"  # Tariff at midnight cannot classify the entire day.
    intraday = point(60, 500, 1500)
    intraday.tariff = "HC"
    result = serialize_energy_history(
        [daily, intraday],
        start=START,
        end=START + timedelta(days=1),
    )
    assert [row["energy_kwh"] for row in result] == [18, 0.5]
    assert [row["tariff"] for row in result] == [None, "HC"]


def test_23_hour_dst_day_is_not_assigned_to_one_tariff() -> None:
    daily = point(0, 10000, 23 * 3600)
    daily.tariff = "HC"
    result = serialize_energy_history(
        [daily], start=START, end=START + timedelta(days=1)
    )
    assert result[0]["tariff"] is None


def test_serializes_native_tariff_split_for_daily_total() -> None:
    daily = point(0, 20623, 86400)
    daily.peak_energy = 14955
    daily.off_peak_energy = 5668
    result = serialize_energy_history(
        [daily], start=START, end=START + timedelta(days=1)
    )
    assert result[0]["energy_kwh"] == pytest.approx(20.623)
    assert result[0]["peak_kwh"] == pytest.approx(14.955)
    assert result[0]["off_peak_kwh"] == pytest.approx(5.668)
    assert result[0]["tariff"] is None


@pytest.mark.parametrize("limit", [0, -1, 3001])
def test_rejects_invalid_history_limits(limit: int) -> None:
    with pytest.raises(ValueError, match="between 1 and 3000"):
        serialize_energy_history(
            [point(0, 100)],
            start=START,
            end=START + timedelta(hours=1),
            limit=limit,
        )


def test_late_arriving_intervals_are_sorted_without_inventing_gaps() -> None:
    """A batch of delayed readings must preserve its real source intervals."""
    result = serialize_energy_history(
        [point(90, 300), point(0, 100), point(30, 200)],
        start=START,
        end=START + timedelta(hours=2),
    )
    assert [row["timestamp"] for row in result] == [
        (START + timedelta(minutes=minute)).isoformat() for minute in (0, 30, 90)
    ]
    assert [row["energy_kwh"] for row in result] == [0.1, 0.2, 0.3]
    assert len(result) == 3


def test_excludes_readings_outside_both_history_boundaries() -> None:
    result = serialize_energy_history(
        [point(-30, 100), point(0, 200), point(60, 300)],
        start=START,
        end=START + timedelta(hours=1),
    )
    assert len(result) == 1
    assert result[0]["energy_kwh"] == pytest.approx(0.2)


def test_preserves_distinct_native_hp_hc_intervals() -> None:
    hp = point(0, 450)
    hp.tariff = "HP"
    hc = point(30, 250)
    hc.tariff = "HC"
    result = serialize_energy_history(
        [hc, hp],
        start=START,
        end=START + timedelta(hours=1),
    )
    assert [row["tariff"] for row in result] == ["HP", "HC"]
    assert sum(row["energy_kwh"] for row in result) == pytest.approx(0.7)


def test_exact_history_limit_is_allowed() -> None:
    result = serialize_energy_history(
        [point(0, 100), point(30, 200)],
        start=START,
        end=START + timedelta(hours=1),
        limit=2,
    )
    assert len(result) == 2
