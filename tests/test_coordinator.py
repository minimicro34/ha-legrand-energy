"""Tests for the Legrand Energy coordinator."""

from __future__ import annotations

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
