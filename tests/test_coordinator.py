"""Tests for the Legrand Energy coordinator."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.legrand_energy.api import (
    LegrandEnergyApiError,
    LegrandEnergyAuthenticationError,
)
from custom_components.legrand_energy.coordinator import LegrandEnergyCoordinator
from custom_components.legrand_energy.models import (
    LegrandEnergyData,
    LegrandMeasurements,
    LegrandModule,
    LegrandProjections,
)
from custom_components.legrand_energy.models.contract import Contract
from custom_components.legrand_energy.private_api import (
    LegrandPrivateApiAuthenticationError,
    LegrandPrivateApiRateLimitError,
)
from custom_components.legrand_energy.tariff_engine import TariffState


def _coordinator(hass, *, private: bool = True) -> LegrandEnergyCoordinator:
    entry = MagicMock()
    entry.entry_id = "entry-id"
    entry.domain = "legrand_energy"
    entry.title = "Legrand EcoMeter"
    api = MagicMock()
    private_api = MagicMock() if private else None
    return LegrandEnergyCoordinator(hass, entry, api, private_api)


@pytest.mark.asyncio
async def test_update_without_private_api(hass) -> None:
    coordinator = _coordinator(hass, private=False)
    module = LegrandModule(id="main", name="EcoMeter", type="NLE")
    coordinator._module_service.async_get = AsyncMock(return_value={"main": module})
    coordinator.api.get_first_home_id.return_value = "home-id"

    data = await coordinator._async_update_data()

    assert data.modules == {"main": module}
    assert data.contract is None
    assert data.measurements is None


@pytest.mark.asyncio
async def test_update_with_contract_and_measurements(hass) -> None:
    coordinator = _coordinator(hass)
    module = LegrandModule(id="main", name="EcoMeter", type="NLE")
    contract = Contract(
        id="contract",
        type="electricity",
        tariff="base",
        tariff_option="base",
        power_threshold=6000,
        power_unit="VA",
        peak_price=0.25,
        off_peak_price=0.18,
        zones=[],
        timetable=[],
    )
    measurements = LegrandMeasurements(energy_today=1.2)
    projections = LegrandProjections(energy_end_of_day=2.3)
    tariff = MagicMock(spec=TariffState)

    coordinator._module_service.async_get = AsyncMock(return_value={"main": module})
    coordinator.api.get_first_home_id.return_value = "home-id"
    coordinator._contract_service.async_get = AsyncMock(return_value=contract)
    coordinator._measurement_service.async_get_all = AsyncMock(
        return_value=(measurements, {"main": measurements}, {}, {}, projections)
    )

    with patch(
        "custom_components.legrand_energy.coordinator.TariffEngine.current_state",
        return_value=tariff,
    ):
        data = await coordinator._async_update_data()

    assert data.contract is contract
    assert data.tariff is tariff
    assert data.measurements is measurements
    assert data.measurements_by_module["main"] is measurements
    assert data.projections is projections


@pytest.mark.asyncio
async def test_invalid_tariff_keeps_update_running(hass) -> None:
    coordinator = _coordinator(hass)
    module = LegrandModule(id="main", name="EcoMeter", type="NLE")
    contract = Contract(
        id="contract",
        type="electricity",
        tariff="base",
        tariff_option="base",
        power_threshold=6000,
        power_unit="VA",
        peak_price=0.25,
        off_peak_price=0.18,
        zones=[],
        timetable=[],
    )
    coordinator._module_service.async_get = AsyncMock(return_value={"main": module})
    coordinator.api.get_first_home_id.return_value = "home-id"
    coordinator._contract_service.async_get = AsyncMock(return_value=contract)
    coordinator._measurement_service.async_get_all = AsyncMock(
        return_value=(None, {}, {}, {}, None)
    )

    with patch(
        "custom_components.legrand_energy.coordinator.TariffEngine.current_state",
        side_effect=ValueError("bad tariff"),
    ):
        data = await coordinator._async_update_data()

    assert data.tariff is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (LegrandPrivateApiRateLimitError("rate"), "rate limit"),
        (LegrandPrivateApiAuthenticationError("auth"), "Private Netatmo"),
        (LegrandEnergyApiError("api"), "Unable to update"),
    ],
)
async def test_update_errors_without_previous_data(hass, error, expected) -> None:
    coordinator = _coordinator(hass)
    coordinator._module_service.async_get = AsyncMock(side_effect=error)

    with pytest.raises(UpdateFailed, match=expected):
        await coordinator._async_update_data()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        LegrandPrivateApiRateLimitError("rate"),
        LegrandPrivateApiAuthenticationError("auth"),
    ],
)
async def test_private_errors_keep_previous_data(hass, error) -> None:
    coordinator = _coordinator(hass)
    previous = LegrandEnergyData(modules={})
    coordinator.data = previous
    coordinator._module_service.async_get = AsyncMock(side_effect=error)

    assert await coordinator._async_update_data() is previous


@pytest.mark.asyncio
async def test_oauth_error_requests_reauthentication(hass) -> None:
    coordinator = _coordinator(hass)
    coordinator._module_service.async_get = AsyncMock(
        side_effect=LegrandEnergyAuthenticationError("expired")
    )

    with pytest.raises(ConfigEntryAuthFailed, match="OAuth authentication expired"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_homestatus_diagnostic_without_private_api(hass, caplog) -> None:
    coordinator = _coordinator(hass, private=False)
    await coordinator.async_debug_homestatus()
    assert "Private Home + Control API is unavailable" in caplog.text


@pytest.mark.asyncio
async def test_homestatus_diagnostic_without_home(hass, caplog) -> None:
    coordinator = _coordinator(hass)
    coordinator.api.get_first_home_id.return_value = None
    coordinator.private_api.homestatus = AsyncMock()
    await coordinator.async_debug_homestatus()
    coordinator.private_api.homestatus.assert_not_awaited()
    assert "no home found" in caplog.text


@pytest.mark.asyncio
async def test_homestatus_diagnostic_summarizes_nested_fields(hass, caplog) -> None:
    coordinator = _coordinator(hass)
    coordinator.api.get_first_home_id.return_value = "home-1"
    coordinator.private_api.homestatus = AsyncMock(
        return_value={
            "modules": [{"type": "NLE", "power": 120, "details": {"current": 3.5}}],
            "energy": [1, 2],
        }
    )
    await coordinator.async_debug_homestatus()
    coordinator.private_api.homestatus.assert_awaited_once_with("home-1")
    assert "NLE" in caplog.text
    assert "root.modules[0].power=120" in caplog.text
    assert "root.modules[0].details.current=3.5" in caplog.text
    assert "root.energy=<list>" in caplog.text


@pytest.mark.asyncio
async def test_tariff_diagnostic_without_contract(hass, caplog) -> None:
    coordinator = _coordinator(hass, private=False)
    await coordinator.async_debug_tariff_fields()
    assert "contract=unavailable" in caplog.text


@pytest.mark.asyncio
async def test_native_price_diagnostic_without_private_data(hass, caplog) -> None:
    coordinator = _coordinator(hass, private=False)
    await coordinator.async_debug_native_price_fields()
    assert "private API/data unavailable" in caplog.text


@pytest.mark.asyncio
async def test_native_price_diagnostic_without_home_or_module(hass, caplog) -> None:
    coordinator = _coordinator(hass)
    coordinator.data = LegrandEnergyData(modules={})
    coordinator.api.get_first_home_id.return_value = "home-1"
    coordinator.private_api.get_home_measure = AsyncMock()
    await coordinator.async_debug_native_price_fields()
    coordinator.private_api.get_home_measure.assert_not_awaited()
    assert "home/total module unavailable" in caplog.text


def test_cached_energy_history_without_service_or_data(hass) -> None:
    coordinator = _coordinator(hass, private=False)
    start = datetime(2026, 11, 5, tzinfo=UTC)
    end = datetime(2026, 11, 6, tzinfo=UTC)
    assert coordinator.cached_energy_history(start=start, end=end) == []
    coordinator = _coordinator(hass)
    coordinator.data = LegrandEnergyData(modules={})
    assert coordinator.cached_energy_history(start=start, end=end) == []



@pytest.mark.asyncio
async def test_tariff_diagnostic_logs_midnight_samples(hass, caplog) -> None:
    coordinator = _coordinator(hass)
    contract = Contract(
        id="contract",
        type="electricity",
        tariff="base",
        tariff_option="base",
        power_threshold=6000,
        power_unit="VA",
        peak_price=0.25,
        off_peak_price=0.18,
        zones=[],
        timetable=[],
    )
    coordinator.data = LegrandEnergyData(modules={}, contract=contract)
    state = MagicMock(spec=TariffState)
    state.zone_id = "hp"
    state.zone_name = "Peak"
    state.is_off_peak = False
    state.price = 0.25
    state.next_change = None

    with patch(
        "custom_components.legrand_energy.coordinator.TariffEngine.state_at",
        return_value=state,
    ) as state_at:
        await coordinator.async_debug_tariff_fields()

    assert state_at.call_count == 5
    assert "sample=previous_day_2359" in caplog.text
    assert "sample=next_day_0000" in caplog.text
    assert "zone_id=hp" in caplog.text


@pytest.mark.asyncio
async def test_tariff_diagnostic_handles_invalid_sample(hass, caplog) -> None:
    coordinator = _coordinator(hass)
    contract = Contract(
        id="contract",
        type="electricity",
        tariff="base",
        tariff_option="base",
        power_threshold=6000,
        power_unit="VA",
        peak_price=0.25,
        off_peak_price=0.18,
        zones=[],
        timetable=[],
    )
    coordinator.data = LegrandEnergyData(modules={}, contract=contract)

    with patch(
        "custom_components.legrand_energy.coordinator.TariffEngine.state_at",
        side_effect=ValueError("invalid timetable"),
    ) as state_at:
        await coordinator.async_debug_tariff_fields()

    assert state_at.call_count == 5
    assert "error=invalid timetable" in caplog.text


@pytest.mark.asyncio
async def test_native_price_diagnostic_handles_measure_failure(hass, caplog) -> None:
    coordinator = _coordinator(hass)
    module = LegrandModule(
        id="main#5", name="Total", type="NLE", bridge="bridge-1"
    )
    coordinator.data = LegrandEnergyData(modules={module.id: module})
    coordinator.api.get_first_home_id.return_value = "home-1"
    coordinator.private_api.get_home_measure = AsyncMock(
        side_effect=RuntimeError("temporary outage")
    )

    await coordinator.async_debug_native_price_fields()

    assert coordinator.private_api.get_home_measure.await_count == 1
    assert "gethomemeasure failed (RuntimeError)" in caplog.text


@pytest.mark.asyncio
async def test_native_price_diagnostic_handles_missing_modules(hass, caplog) -> None:
    coordinator = _coordinator(hass)
    module = LegrandModule(
        id="main#5", name="Total", type="NLE", bridge="bridge-1"
    )
    coordinator.data = LegrandEnergyData(modules={module.id: module})
    coordinator.api.get_first_home_id.return_value = "home-1"
    coordinator.private_api.get_home_measure = AsyncMock(
        return_value={"body": {"home": {}}}
    )

    await coordinator.async_debug_native_price_fields()

    assert coordinator.private_api.get_home_measure.await_count == 1
    assert "response_modules=missing" in caplog.text
