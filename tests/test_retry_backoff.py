"""Tests for retry backoff helper."""

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.legrand_energy.helpers.retry_backoff import RetryBackoff


def test_requires_at_least_one_delay() -> None:
    """Reject an empty retry schedule."""
    with pytest.raises(
        ValueError,
        match="At least one retry delay is required",
    ):
        RetryBackoff(())


def test_is_ready_before_any_failure() -> None:
    """Allow attempts before any failure occurs."""
    now = datetime(2026, 8, 4, 12, tzinfo=UTC)
    backoff = RetryBackoff((timedelta(minutes=2),))

    assert backoff.is_ready(now)
    assert backoff.failure_count == 0
    assert backoff.retry_at is None


def test_progressive_retry_delays() -> None:
    """Apply each configured delay after consecutive failures."""
    now = datetime(2026, 8, 4, 12, tzinfo=UTC)
    backoff = RetryBackoff(
        (
            timedelta(minutes=2),
            timedelta(minutes=5),
            timedelta(minutes=10),
            timedelta(minutes=15),
        )
    )

    expected_delays = (
        timedelta(minutes=2),
        timedelta(minutes=5),
        timedelta(minutes=10),
        timedelta(minutes=15),
    )

    for failure_count, expected_delay in enumerate(
        expected_delays,
        start=1,
    ):
        delay = backoff.record_failure(now)

        assert delay == expected_delay
        assert backoff.failure_count == failure_count
        assert backoff.retry_at == now + expected_delay
        assert not backoff.is_ready(now + expected_delay - timedelta(seconds=1))
        assert backoff.is_ready(now + expected_delay)

        now += expected_delay


def test_reuses_last_delay_after_schedule_is_exhausted() -> None:
    """Reuse the final delay for later consecutive failures."""
    now = datetime(2026, 8, 4, 12, tzinfo=UTC)
    backoff = RetryBackoff(
        (
            timedelta(minutes=2),
            timedelta(minutes=5),
        )
    )

    assert backoff.record_failure(now) == timedelta(minutes=2)
    assert backoff.record_failure(now) == timedelta(minutes=5)
    assert backoff.record_failure(now) == timedelta(minutes=5)
    assert backoff.failure_count == 3


def test_reset_returns_previous_failure_count() -> None:
    """Clear retry state and return the number of failures."""
    now = datetime(2026, 8, 4, 12, tzinfo=UTC)
    backoff = RetryBackoff((timedelta(minutes=2),))

    backoff.record_failure(now)
    backoff.record_failure(now)

    assert backoff.reset() == 2
    assert backoff.failure_count == 0
    assert backoff.retry_at is None
    assert backoff.is_ready(now)
    assert backoff.reset() == 0
