"""Tests for electricity measurement orchestration."""

from datetime import UTC, datetime
from typing import Any, cast

import pytest

from custom_components.legrand_energy import measurement_service as service_module
from custom_components.legrand_energy.measurement_service import MeasurementService
from custom_components.legrand_energy.models import LegrandModule
from custom_components.legrand_energy.private_api import LegrandPrivateApi

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
    """Return separate historical and current-day responses."""

    def __init__(self) -> None:
        """Initialize recorded calls."""
        self.calls: list[dict[str, Any]] = []

    async def get_electricity_measures(self, **kwargs: Any) -> dict[str, Any]:
        """Return data matching the requested scale."""
        self.calls.append(kwargs)
        if kwargs["scale"] == "1day":
            return _response(
                (datetime(2026, 7, 1, tzinfo=UTC), 10_000.0, 2.0),
                (datetime(2026, 7, 28, tzinfo=UTC), 2_000.0, 0.4),
            )
        return _response(
            (datetime(2026, 7, 31, 12, tzinfo=UTC), 1_000.0, 0.2),
        )


@pytest.mark.asyncio
async def test_fetches_year_history_and_current_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build each period from year history plus detailed current-day data."""
    now = datetime(2026, 7, 31, 12, tzinfo=UTC)
    monkeypatch.setattr(service_module.dt_util, "now", lambda: now)
    api = FakePrivateApi()
    service = MeasurementService(cast(LegrandPrivateApi, api))

    measurements, _, _ = await service.async_get_all(
        home_id="home-id",
        modules={
            MODULE_ID: LegrandModule(
                id=MODULE_ID,
                name="Total",
                type="NLE",
                bridge="bridge-id",
            )
        },
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
