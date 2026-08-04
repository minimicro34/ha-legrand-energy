"""Retry backoff helper."""

from __future__ import annotations

from datetime import datetime, timedelta


class RetryBackoff:
    """Track retry timing after consecutive failures."""

    def __init__(
        self,
        delays: tuple[timedelta, ...],
    ) -> None:
        """Initialize the retry backoff."""
        if not delays:
            raise ValueError("At least one retry delay is required")

        self._delays = delays
        self._failure_count = 0
        self._retry_at: datetime | None = None

    @property
    def failure_count(self) -> int:
        """Return the number of consecutive failures."""
        return self._failure_count

    @property
    def retry_at(self) -> datetime | None:
        """Return the next allowed retry time."""
        return self._retry_at

    def is_ready(self, now: datetime) -> bool:
        """Return whether another attempt may be made."""
        return self._retry_at is None or now >= self._retry_at

    def record_failure(self, now: datetime) -> timedelta:
        """Record a failure and return the selected retry delay."""
        delay_index = min(
            self._failure_count,
            len(self._delays) - 1,
        )
        delay = self._delays[delay_index]

        self._failure_count += 1
        self._retry_at = now + delay

        return delay

    def reset(self) -> int:
        """Reset the backoff and return the previous failure count."""
        previous_failure_count = self._failure_count

        self._failure_count = 0
        self._retry_at = None

        return previous_failure_count
