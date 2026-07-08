"""Tests for monthly projections."""

from datetime import UTC, datetime

from custom_components.legrand_energy.helpers.monthly_projection import (
    project_month,
)


def test_month_projection() -> None:
    """Test month projection."""
    projection = project_month(
        energy=50,
        cost=10,
        now=datetime(2026, 7, 16, 0, 0, tzinfo=UTC),
    )

    assert projection.projected_energy > 90
    assert projection.projected_cost > 18