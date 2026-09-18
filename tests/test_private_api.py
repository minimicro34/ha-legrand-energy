"""Tests for the private Legrand Energy API client."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.legrand_energy.models.auth import PrivateSession
from custom_components.legrand_energy.models.fluid import FluidType
from custom_components.legrand_energy.private_api import (
    APP_API_BASE,
    LegrandPrivateApi,
    LegrandPrivateApiAuthenticationError,
    LegrandPrivateApiError,
    LegrandPrivateApiRateLimitError,
)
from custom_components.legrand_energy.services.private import (
    PrivateAuthServiceAuthenticationError,
    PrivateAuthServiceError,
)


def _api() -> tuple[LegrandPrivateApi, MagicMock]:
    authentication = MagicMock()
    authentication.private.web_token = "private-token"
    authentication.private_headers = {"Authorization": "Bearer private-token"}
    authentication.refresh_private = AsyncMock(
        return_value=PrivateSession(web_token="new-token", cookies={})
    )
    return LegrandPrivateApi(MagicMock(), authentication), authentication


def _response(status: int, *, text: str = "") -> MagicMock:
    response = MagicMock()
    response.status = status
    response.text = text
    return response


def test_private_properties() -> None:
    api, _ = _api()
    assert api.web_token == "private-token"
    assert api._headers() == {"Authorization": "Bearer private-token"}


@pytest.mark.asyncio
async def test_get_success_and_auth_retry() -> None:
    api, authentication = _api()
    api._request = AsyncMock(
        side_effect=[_response(401), _response(200)]
    )
    api._parse_json_response = MagicMock(return_value={"body": {"ok": True}})

    result = await api._get(APP_API_BASE, "homestatus")

    assert result == {"body": {"ok": True}}
    authentication.refresh_private.assert_awaited_once()
    assert api._request.await_count == 2


@pytest.mark.asyncio
async def test_get_errors() -> None:
    api, _ = _api()

    api._request = AsyncMock(return_value=_response(403))
    with pytest.raises(
        LegrandPrivateApiAuthenticationError, match="after authentication refresh"
    ):
        await api._get(APP_API_BASE, "homestatus", retry_auth=False)

    api._request = AsyncMock(return_value=_response(429, text="slow down"))
    with pytest.raises(LegrandPrivateApiRateLimitError, match="rate limit"):
        await api._get(APP_API_BASE, "homestatus")

    api._request = AsyncMock(return_value=_response(500, text="server error"))
    with pytest.raises(LegrandPrivateApiError, match="HTTP status 500"):
        await api._get(APP_API_BASE, "homestatus")

    api._request = AsyncMock(return_value=_response(200))
    api._parse_json_response = MagicMock(
        return_value={"status": "error", "error": {"message": "bad"}}
    )
    with pytest.raises(LegrandPrivateApiError, match="API error"):
        await api._get(APP_API_BASE, "homestatus")


@pytest.mark.asyncio
async def test_homestatus_and_getcontracts() -> None:
    api, _ = _api()
    api._get = AsyncMock(side_effect=[{"status": "ok"}, {"contract": "ok"}])

    assert await api.homestatus("home-id") == {"status": "ok"}
    first_call = api._get.await_args_list[0]
    assert first_call.args == (
        APP_API_BASE,
        "homestatus",
        {"home_id": "home-id"},
    )

    assert await api.getcontracts("home-id") == {"contract": "ok"}
    second_call = api._get.await_args_list[1]
    assert second_call.args == (
        APP_API_BASE,
        "getcontracts",
        {"home_id": "home-id"},
    )


@pytest.mark.asyncio
async def test_get_home_measure_builds_params() -> None:
    api, _ = _api()
    api._get = AsyncMock(return_value={"body": {}})
    home = {"id": "home-id", "modules": []}

    await api.get_home_measure(
        home=home,
        scale="30min",
        real_time=False,
        date_begin=100,
        date_end=200,
    )

    call = api._get.await_args
    assert call.args[0:2] == (APP_API_BASE, "gethomemeasure")
    params = call.args[2]
    assert json.loads(params["home"]) == home
    assert params["real_time"] == "false"
    assert params["scale"] == "30min"
    assert params["date_begin"] == 100
    assert params["date_end"] == 200

    await api.get_home_measure(home=home)
    params = api._get.await_args.args[2]
    assert "date_begin" not in params
    assert "date_end" not in params
    assert params["real_time"] == "true"


@pytest.mark.asyncio
async def test_get_measure_builds_probe_payload() -> None:
    api, _ = _api()
    api._get = AsyncMock(return_value={"body": {}})

    await api.get_measure("home-id", "module-id", "power", bridge="bridge-id")
    params = api._get.await_args.args[2]
    payload = json.loads(params["home"])
    assert payload["id"] == "home-id"
    assert payload["modules"] == [
        {"id": "module-id", "type": "power", "bridge": "bridge-id"}
    ]
    assert params["scale"] == "max"
    assert params["date_end"] == "last"

    await api.get_measure("home-id", "module-id", "power")
    payload = json.loads(api._get.await_args.args[2]["home"])
    assert "bridge" not in payload["modules"][0]


@pytest.mark.asyncio
async def test_electricity_and_fluid_measure_helpers() -> None:
    api, _ = _api()
    api._get = AsyncMock(return_value={"body": {}})

    await api.get_electricity_measure(
        "home-id", "module-id", "bridge-id", 100, 200
    )
    params = api._get.await_args.args[2]
    payload = json.loads(params["home"])
    assert payload["modules"][0]["id"] == "module-id"
    assert payload["modules"][0]["bridge"] == "bridge-id"
    assert params["scale"] == "5min"
    assert params["date_begin"] == 100
    assert params["date_end"] == 200

    await api.get_fluid_measures(
        "home-id",
        [("module-1", "bridge-1"), ("module-2", "bridge-2")],
        FluidType.ELECTRICITY,
        300,
        400,
        scale="30min",
    )
    params = api._get.await_args.args[2]
    payload = json.loads(params["home"])
    assert [module["id"] for module in payload["modules"]] == [
        "module-1",
        "module-2",
    ]
    assert params["scale"] == "30min"

    api.get_fluid_measures = AsyncMock(return_value={"body": {"ok": True}})
    result = await api.get_electricity_measures(
        "home-id",
        [("module-1", "bridge-1")],
        500,
        600,
        scale="1hour",
    )
    assert result == {"body": {"ok": True}}
    api.get_fluid_measures.assert_awaited_once_with(
        home_id="home-id",
        modules=[("module-1", "bridge-1")],
        fluid_type=FluidType.ELECTRICITY,
        date_begin=500,
        date_end=600,
        scale="1hour",
    )


@pytest.mark.asyncio
async def test_refresh_web_token() -> None:
    api, authentication = _api()
    assert await api.refresh_web_token() == "new-token"

    authentication.refresh_private.side_effect = (
        PrivateAuthServiceAuthenticationError("expired")
    )
    with pytest.raises(
        LegrandPrivateApiAuthenticationError, match="Unable to refresh"
    ):
        await api.refresh_web_token()

    authentication.refresh_private.side_effect = PrivateAuthServiceError("network")
    with pytest.raises(LegrandPrivateApiError, match="Unable to refresh"):
        await api.refresh_web_token()
