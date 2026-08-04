"""Tests for electricity and fluid measurement orchestration."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from custom_components.legrand_energy import measurement_service as service_module
from custom_components.legrand_energy.measurement_service import MeasurementService
from custom_components.legrand_energy.models import FluidType, LegrandModule
from custom_components.legrand_energy.private_api import (
    LegrandPrivateApi,
    LegrandPrivateApiError,
)

ELECTRICITY_MODULE_ID = "00:04:74:12:24:d4#5"
WATER_MODULE_ID = "00:04:74:12:24:d4#8"
GAS_MODULE_ID = "00:04:74:12:24:d4#6"


def _response(
    module_id: str,
    *points: tuple[datetime, float, float],
) -> dict[str, Any]:
    """Build a minimal Home Control electricity response."""
    return {
        "body": {
            "home": {
                "modules": [
                    {
                        "id": module_id,
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


def _empty_response(module_id: str) -> dict[str, Any]:
    """Build a response containing a module without measurements."""
    return {
        "body": {
            "home": {
                "modules": [
                    {
                        "id": module_id,
                        "measures": [],
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
        """Return data matching the requested scale and fluid type."""
        self.calls.append(kwargs)

        fluid_type = kwargs["fluid_type"]
        module_id = kwargs["modules"][0][0]

        if fluid_type is FluidType.WATER:
            return _empty_response(module_id)

        if fluid_type is FluidType.GAS:
            return _empty_response(module_id)

        if kwargs["scale"] == "1day":
            if self.historical_failures:
                self.historical_failures -= 1
                raise LegrandPrivateApiError("temporary historical failure")

            return _response(
                module_id,
                (datetime(2026, 7, 1, tzinfo=UTC), 10_000.0, 2.0),
                (datetime(2026, 7, 28, tzinfo=UTC), 2_000.0, 0.4),
            )

        return _response(
            module_id,
            (datetime(2026, 7, 31, 12, tzinfo=UTC), 1_000.0, 0.2),
        )


def _modules() -> dict[str, LegrandModule]:
    """Return the total electricity module."""
    return {
        ELECTRICITY_MODULE_ID: LegrandModule(
            id=ELECTRICITY_MODULE_ID,
            name="Total",
            type="NLE",
            fluid_type=FluidType.ELECTRICITY,
            bridge="bridge-id",
        )
    }


def _modules_with_fluids() -> dict[str, LegrandModule]:
    """Return electricity, water, and gas modules."""
    return {
        ELECTRICITY_MODULE_ID: LegrandModule(
            id=ELECTRICITY_MODULE_ID,
            name="Total",
            type="NLE",
            fluid_type=FluidType.ELECTRICITY,
            bridge="bridge-id",
        ),
        WATER_MODULE_ID: LegrandModule(
            id=WATER_MODULE_ID,
            name="Eau froide",
            type="NLE",
            fluid_type=FluidType.WATER,
            bridge="bridge-id",
        ),
        GAS_MODULE_ID: LegrandModule(
            id=GAS_MODULE_ID,
            name="Gaz",
            type="NLE",
            fluid_type=FluidType.GAS,
            bridge="bridge-id",
        ),
    }


async def _update(service: MeasurementService) -> None:
    """Run one electricity measurement update."""
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


@pytest.mark.asyncio
async def test_empty_water_and_gas_measurements_return_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expose zero consumption when fluid modules contain no measurements."""
    now = datetime(2026, 7, 31, 12, tzinfo=UTC)
    monkeypatch.setattr(service_module.dt_util, "now", lambda: now)

    api = FakePrivateApi()
    service = MeasurementService(cast(LegrandPrivateApi, api))

    (
        _,
        _,
        water_measurements,
        gas_measurements,
        _,
    ) = await service.async_get_all(
        home_id="home-id",
        modules=_modules_with_fluids(),
        contract=None,
        tariff_engine=None,
        previous_data=None,
    )

    water = water_measurements[WATER_MODULE_ID]
    gas = gas_measurements[GAS_MODULE_ID]

    assert water.consumption_today == 0.0
    assert water.consumption_week == 0.0
    assert water.consumption_month == 0.0
    assert water.consumption_year == 0.0

    assert water.cost_today == 0.0
    assert water.cost_week == 0.0
    assert water.cost_month == 0.0
    assert water.cost_year == 0.0

    assert gas.consumption_today == 0.0
    assert gas.consumption_week == 0.0
    assert gas.consumption_month == 0.0
    assert gas.consumption_year == 0.0

    assert gas.cost_today == 0.0
    assert gas.cost_week == 0.0
    assert gas.cost_month == 0.0
    assert gas.cost_year == 0.0
