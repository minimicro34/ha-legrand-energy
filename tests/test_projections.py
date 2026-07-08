"""Tests for projection helpers."""

from datetime import UTC, datetime

from custom_components.legrand_energy.helpers.projections import project_today


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