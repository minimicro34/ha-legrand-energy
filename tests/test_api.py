"""Tests for the Legrand Energy API client."""

from __future__ import annotations

from datetime import timedelta
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.legrand_energy.api import (
    LegrandEnergyApi,
    LegrandEnergyApiError,
    LegrandEnergyHttpError,
    LegrandEnergyAuthenticationError,
)
from custom_components.legrand_energy.authentication import AuthenticationError


def _api() -> tuple[LegrandEnergyApi, MagicMock]:
    authentication = MagicMock()
    authentication.authorization_headers = {"Authorization": "Bearer oauth"}
    authentication.async_ensure_oauth_valid = AsyncMock()
    return LegrandEnergyApi(MagicMock(), authentication), authentication


def _response(status: int, data: dict) -> MagicMock:
    response = MagicMock()
    response.status = status
    return response


def test_error_helpers() -> None:
    assert LegrandEnergyApi._get_error_code({}) is None
    assert LegrandEnergyApi._get_error_code({"error": {"code": 2}}) == 2
    assert LegrandEnergyApi._get_error_code({"error": {"code": "3"}}) == 3
    assert LegrandEnergyApi._get_error_code({"error": {"code": "bad"}}) is None
    assert LegrandEnergyApi._get_error_code({"error": "bad"}) is None

    assert LegrandEnergyApi._response_has_error(500, {}) is True
    assert LegrandEnergyApi._response_has_error(200, {"status": "error"}) is True
    assert LegrandEnergyApi._response_has_error(200, {"error": {"code": 1}}) is True
    assert LegrandEnergyApi._response_has_error(200, {}) is False

    message = LegrandEnergyApi._build_error_message(
        "GET", "homesdata", 400, 42, {"error": {"message": "bad request"}}
    )
    assert "HTTP 400" in message
    assert "code=42" in message
    assert "bad request" in message


@pytest.mark.asyncio
async def test_get_success_and_auth_retry() -> None:
    api, authentication = _api()
    first = _response(200, {})
    second = _response(200, {})
    api._request = AsyncMock(side_effect=[first, second])
    api._parse_json_response = MagicMock(
        side_effect=[{"error": {"code": 2}}, {"body": {"ok": True}}]
    )

    result = await api._get("homesdata")

    assert result == {"body": {"ok": True}}
    authentication.async_ensure_oauth_valid.assert_awaited_once()
    assert api._request.await_count == 2


@pytest.mark.asyncio
async def test_get_auth_and_api_errors() -> None:
    api, authentication = _api()
    api._request = AsyncMock(return_value=_response(401, {}))
    api._parse_json_response = MagicMock(return_value={"error": {"code": 2}})
    authentication.async_ensure_oauth_valid.side_effect = AuthenticationError("refresh")

    with pytest.raises(LegrandEnergyAuthenticationError, match="refresh failed"):
        await api._get("homesdata")

    authentication.async_ensure_oauth_valid.side_effect = None
    with pytest.raises(LegrandEnergyAuthenticationError, match="Authentication failed"):
        await api._get("homesdata", retry=False)

    api._parse_json_response = MagicMock(
        return_value={"error": {"code": 42, "message": "failure"}}
    )
    with pytest.raises(LegrandEnergyApiError, match="code=42"):
        await api._get("homesdata", retry=False)


@pytest.mark.asyncio
async def test_post_success_retry_and_errors() -> None:
    api, authentication = _api()
    api._request = AsyncMock(return_value=_response(200, {}))
    api._parse_json_response = MagicMock(return_value={"body": {"ok": True}})
    assert await api._post("endpoint", {"foo": "bar"}) == {"body": {"ok": True}}

    api._request = AsyncMock(side_effect=[_response(200, {}), _response(200, {})])
    api._parse_json_response = MagicMock(
        side_effect=[{"error": {"code": "3"}}, {"body": {"ok": True}}]
    )
    assert await api._post("endpoint") == {"body": {"ok": True}}
    authentication.async_ensure_oauth_valid.assert_awaited()

    api._request = AsyncMock(return_value=_response(401, {}))
    api._parse_json_response = MagicMock(return_value={"error": {"code": 3}})
    with pytest.raises(LegrandEnergyAuthenticationError):
        await api._post("endpoint", retry=False)

    api._parse_json_response = MagicMock(
        return_value={"error": {"code": 99, "message": "bad"}}
    )
    with pytest.raises(LegrandEnergyApiError, match="code=99"):
        await api._post("endpoint", retry=False)


@pytest.mark.asyncio
async def test_homesdata_cache_and_simple_endpoints() -> None:
    api, _ = _api()
    api._get = AsyncMock(
        side_effect=[
            {"body": {"homes": []}},
            {"body": {"homes": ["fresh"]}},
            {"status": "home"},
            {"contracts": []},
        ]
    )

    first = await api.homesdata()
    assert await api.homesdata() is first
    assert api._get.await_count == 1

    fresh = await api.homesdata(force_refresh=True)
    assert fresh == {"body": {"homes": ["fresh"]}}
    assert await api.homestatus() == {"status": "home"}
    assert await api.contracts() == {"contracts": []}


@pytest.mark.asyncio
async def test_homesdata_periodic_refresh_and_forced_refresh() -> None:
    """The sync request is repeated after 15 minutes, not every poll."""
    api, _ = _api()
    api._get = AsyncMock(
        side_effect=[
            {"body": {"homes": ["initial"]}},
            {"body": {"homes": ["periodic"]}},
            {"body": {"homes": ["forced"]}},
        ]
    )

    initial = await api.homesdata()
    assert api._get.await_count == 1
    assert api._get.await_args.kwargs["params"]["sync_measurements"] == "true"

    # Still cached just before the 15-minute threshold.
    api._homes_data_fetched_at -= timedelta(minutes=14, seconds=59)
    assert await api.homesdata() is initial
    assert api._get.await_count == 1

    # The next coordinator poll must request a fresh sync.
    api._homes_data_fetched_at -= timedelta(seconds=2)
    periodic = await api.homesdata()
    assert periodic == {"body": {"homes": ["periodic"]}}
    assert api._get.await_count == 2
    assert api._get.await_args.args[0] == "homesdata"
    assert api._get.await_args.kwargs["params"]["sync_measurements"] == "true"

    # Explicit refresh bypasses the newly updated cache.
    forced = await api.homesdata(force_refresh=True)
    assert forced == {"body": {"homes": ["forced"]}}
    assert api._get.await_count == 3


@pytest.mark.asyncio
async def test_discover_modules() -> None:
    api, _ = _api()
    api.homesdata = AsyncMock(
        return_value={
            "body": {
                "homes": [
                    {
                        "rooms": [
                            {"id": "room-1", "name": "Garage"},
                            {"id": 123, "name": "ignored"},
                        ],
                        "modules": [
                            {
                                "id": "main",
                                "name": "EcoMeter",
                                "type": "NLE",
                                "room_id": "room-1",
                                "setup_date": 123456,
                            },
                            {
                                "id": "main#0",
                                "name": "Circuit",
                                "type": "NLE",
                                "bridge": "main",
                            },
                            {"id": "ignored", "type": "OTHER"},
                            "invalid",
                        ],
                    }
                ]
            }
        }
    )

    modules = await api.discover_modules()
    assert set(modules) == {"main", "main#0"}
    assert modules["main"].room == "Garage"
    assert modules["main"].setup_date == 123456
    assert modules["main#0"].bridge == "main"

    api.homesdata = AsyncMock(return_value={"body": {"homes": "invalid"}})
    with pytest.raises(LegrandEnergyApiError, match="valid homes list"):
        await api.discover_modules()


@pytest.mark.asyncio
async def test_get_home_measure_uses_private_token() -> None:
    api, _ = _api()
    api._get = AsyncMock(return_value={"body": {}})

    result = await api.get_home_measure(
        "home-id",
        "module-id",
        "bridge-id",
        "private-token",
        100,
        200,
    )

    assert result == {"body": {}}
    call = api._get.await_args
    assert call.args[0] == "gethomemeasure"
    assert call.kwargs["headers"]["Authorization"] == "Bearer private-token"
    assert call.kwargs["retry"] is False
    assert call.kwargs["params"]["date_begin"] == 100
    assert call.kwargs["params"]["date_end"] == 200


def test_get_first_home_id() -> None:
    api, _ = _api()
    assert api.get_first_home_id() is None

    api._homes_data = {"body": {"homes": [{"id": "home-id"}]}}
    assert api.get_first_home_id() == "home-id"

    api._homes_data = {"body": {"homes": []}}
    assert api.get_first_home_id() is None

    api._homes_data = {"body": {"homes": ["invalid"]}}
    assert api.get_first_home_id() is None

    api._homes_data = {"body": {"homes": [{"id": 123}]}}
    assert api.get_first_home_id() is None


@pytest.mark.asyncio
async def test_homesdata_5xx_backoff_and_recovery(caplog: pytest.LogCaptureFixture) -> None:
    """Reuse cached topology and progressively delay server-error retries."""
    caplog.set_level(logging.INFO)
    api, _ = _api()
    cached = {"body": {"homes": ["cached"]}}
    fresh = {"body": {"homes": ["recovered"]}}
    api._get = AsyncMock(
        side_effect=[
            cached,
            LegrandEnergyHttpError("server down", 503, 27),
            LegrandEnergyHttpError("gateway", 502, None),
            LegrandEnergyHttpError("internal", 500, None),
            LegrandEnergyHttpError("unavailable", 503, 27),
            fresh,
        ]
    )

    assert await api.homesdata() is cached
    original_fetched_at = api._homes_data_fetched_at

    for count, delay in enumerate((15, 30, 60, 60), start=1):
        api._homes_data_fetched_at -= timedelta(minutes=16)
        assert await api.homesdata() is cached
        assert api._homesdata_backoff.failure_count == count
        assert api._homesdata_backoff.retry_at is not None
        assert api._homesdata_backoff.retry_at - api._homes_data_fetched_at > timedelta(minutes=delay)
        calls = api._get.await_count
        assert await api.homesdata(force_refresh=True) is cached
        assert api._get.await_count == calls
        # Simulate the backoff deadline passing.
        api._homesdata_backoff._retry_at -= timedelta(minutes=61)

    assert await api.homesdata() is fresh
    assert api._homesdata_backoff.failure_count == 0
    assert api._homesdata_backoff.retry_at is None
    assert api._homes_data_fetched_at != original_fetched_at
    assert "recovered after 4 failed update(s)" in caplog.text


@pytest.mark.asyncio
async def test_homesdata_does_not_mask_uncached_or_non_5xx_errors() -> None:
    """Preserve normal errors without a cache or for client failures."""
    api, _ = _api()
    api._get = AsyncMock(side_effect=LegrandEnergyHttpError("down", 503, 27))
    with pytest.raises(LegrandEnergyHttpError):
        await api.homesdata()
    assert api._homesdata_backoff.failure_count == 0

    api._homes_data = {"body": {"homes": []}}
    api._get.side_effect = LegrandEnergyHttpError("bad request", 400, 12)
    with pytest.raises(LegrandEnergyHttpError):
        await api.homesdata(force_refresh=True)
    assert api._homesdata_backoff.failure_count == 0


@pytest.mark.asyncio
async def test_get_exposes_http_status_for_server_errors() -> None:
    """Allow homesdata to distinguish server errors without parsing strings."""
    api, _ = _api()
    api._request = AsyncMock(return_value=_response(503, {}))
    api._parse_json_response = MagicMock(
        return_value={"error": {"code": 27, "message": "unavailable"}}
    )
    with pytest.raises(LegrandEnergyHttpError) as exc:
        await api._get("homesdata")
    assert exc.value.status == 503
    assert exc.value.code == 27
