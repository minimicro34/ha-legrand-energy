"""Tests for projection helpers."""

from datetime import UTC, datetime

import pytest

from custom_components.legrand_energy.helpers.projections import (
    project_month,
    project_today,
)


def test_project_today_at_midday() -> None:
    """Test daily projection at midday."""
    projection = project_today(
        energy=5.0,
        cost=1.0,
        now=datetime(2026, 7, 8, 12, 0, tzinfo=UTC),
    )

    assert projection.elapsed_ratio == 0.5
    assert projection.projected_energy == 10.0
    assert projection.projected_cost == 2.0


def test_project_today_at_midnight() -> None:
    """Test daily projection at midnight."""
    projection = project_today(
        energy=5.0,
        cost=1.0,
        now=datetime(2026, 7, 8, 0, 0, tzinfo=UTC),
    )

    assert projection.elapsed_ratio == 0.0
    assert projection.projected_energy == 0.0
    assert projection.projected_cost == 0.0


@pytest.mark.parametrize(
    ("now", "days_in_month"),
    [
        (datetime(2026, 2, 1, tzinfo=UTC), 28),
        (datetime(2024, 2, 1, tzinfo=UTC), 29),
        (datetime(2026, 7, 1, tzinfo=UTC), 31),
    ],
)
def test_project_month(now: datetime, days_in_month: int) -> None:
    """Test monthly projection for different month lengths."""
    projection = project_month(
        energy=5.0,
        cost=1.0,
        now=now,
    )

    assert projection.projected_energy == 5.0 * days_in_month
    assert projection.projected_cost == 1.0 * days_in_month
    assert projection.elapsed_ratio == pytest.approx(1.0 / days_in_month)
