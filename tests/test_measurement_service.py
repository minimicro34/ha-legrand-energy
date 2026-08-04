"""Tests for electricity measurement orchestration."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from custom_components.legrand_energy import measurement_service as service_module
from custom_components.legrand_energy.measurement_service import MeasurementService
from custom_components.legrand_energy.models import LegrandModule
from custom_components.legrand_energy.private_api import (
    LegrandPrivateApi,
    LegrandPrivateApiError,
)

MODULE_ID = "00:04:74:12:24:d4#5"


def _response(*points: tuple[datetime, float, float]) -> dict[str, Any]:
    """Build a minimal Home Control measurement response."""
    return {
        "body": {
            "home": {
                "modules": [
                    {
                        "id": MODULE_ID,
                        "measures": [
                            {
                                "beg_time": int(timestamp.timestamp()),
                                "step_time": 300,
                                "value": [
                                    [None, energy, None, None, price, None, None]
                                ],
                            }
                            for timestamp, energy, price in points
                        ],
                    }
                ]
            }
        }
    }


class FakePrivateApi:
    """Return controlled historical and current-day responses."""

    def __init__(self) -> None:
        """Initialize recorded calls and failures."""
        self.calls: list[dict[str, Any]] = []
        self.historical_failures = 0

    async def get_fluid_measures(self, **kwargs: Any) -> dict[str, Any]:
        """Return data matching the requested scale."""
        self.calls.append(kwargs)

        if kwargs["scale"] == "1day":
            if self.historical_failures:
                self.historical_failures -= 1
                raise LegrandPrivateApiError("temporary historical failure")

            return _response(
                (datetime(2026, 7, 1, tzinfo=UTC), 10_000.0, 2.0),
                (datetime(2026, 7, 28, tzinfo=UTC), 2_000.0, 0.4),
            )

        return _response(
            (datetime(2026, 7, 31, 12, tzinfo=UTC), 1_000.0, 0.2),
        )


def _modules() -> dict[str, LegrandModule]:
    """Return the total electricity module."""
    return {
        MODULE_ID: LegrandModule(
            id=MODULE_ID,
            name="Total",
            type="NLE",
            bridge="bridge-id",
        )
    }


async def _update(service: MeasurementService) -> None:
    """Run one measurement update."""
    await service.async_get_all(
        home_id="home-id",
        modules=_modules(),
        contract=None,
        tariff_engine=None,
        previous_data=None,
    )


@pytest.mark.asyncio
async def test_fetches_year_history_and_current_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build each period from year history plus current-day data."""
    now = datetime(2026, 7, 31, 12, tzinfo=UTC)
    monkeypatch.setattr(service_module.dt_util, "now", lambda: now)

    api = FakePrivateApi()
    service = MeasurementService(cast(LegrandPrivateApi, api))

    (
        measurements,
        _,
        _,
        _,
        _,
    ) = await service.async_get_all(
        home_id="home-id",
        modules=_modules(),
        contract=None,
        tariff_engine=None,
        previous_data=None,
    )

    assert [call["scale"] for call in api.calls] == ["1day", "5min"]
    assert api.calls[0]["date_begin"] == int(
        datetime(2026, 1, 1, tzinfo=UTC).timestamp()
    )

    assert measurements is not None
    assert measurements.energy_today == 1.0
    assert measurements.energy_week == 3.0
    assert measurements.energy_month == 13.0
    assert measurements.energy_year == 13.0
    assert measurements.cost_month == pytest.approx(2.6)
    assert measurements.cost_year == pytest.approx(2.6)


@pytest.mark.asyncio
async def test_reuses_history_cache_during_same_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fetch history once while current-day data keeps refreshing."""
    now = datetime(2026, 7, 31, 12, tzinfo=UTC)
    monkeypatch.setattr(service_module.dt_util, "now", lambda: now)

    api = FakePrivateApi()
    service = MeasurementService(cast(LegrandPrivateApi, api))

    await _update(service)
    await _update(service)

    assert [call["scale"] for call in api.calls] == [
        "1day",
        "5min",
        "5min",
    ]


@pytest.mark.asyncio
async def test_refreshes_history_after_day_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refresh history when the calendar day changes."""
    current_now = datetime(2026, 7, 31, 23, 59, tzinfo=UTC)
    monkeypatch.setattr(service_module.dt_util, "now", lambda: current_now)

    api = FakePrivateApi()
    service = MeasurementService(cast(LegrandPrivateApi, api))

    await _update(service)

    current_now += timedelta(minutes=2)
    await _update(service)

    assert [call["scale"] for call in api.calls] == [
        "1day",
        "5min",
        "1day",
        "5min",
    ]


@pytest.mark.asyncio
async def test_retries_failed_history_after_fifteen_minutes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delay historical retries while current-day refreshes continue."""
    current_now = datetime(2026, 7, 31, 12, tzinfo=UTC)
    monkeypatch.setattr(service_module.dt_util, "now", lambda: current_now)

    api = FakePrivateApi()
    api.historical_failures = 1
    service = MeasurementService(cast(LegrandPrivateApi, api))

    await _update(service)

    current_now += timedelta(minutes=10)
    await _update(service)

    current_now += timedelta(minutes=5)
    await _update(service)

    assert [call["scale"] for call in api.calls] == [
        "1day",
        "5min",
        "5min",
        "1day",
        "5min",
    ]
