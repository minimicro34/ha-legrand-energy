"""Tests for the shared Legrand Energy API client."""

from __future__ import annotations

from unittest.mock import MagicMock

import aiohttp
import pytest

from custom_components.legrand_energy.base_api import ApiResponse, BaseApiClient


class TestApiError(Exception):
    """Test API error."""


def _client(session: MagicMock | None = None) -> BaseApiClient:
    return BaseApiClient(session or MagicMock(), TestApiError)


@pytest.mark.asyncio
async def test_request_success() -> None:
    response = MagicMock()
    response.status = 200
    response.text.return_value = "payload"
    response.text = MagicMock(return_value="payload")
    response.url = "https://example.test/api"

    request_context = MagicMock()
    request_context.__aenter__ = MagicMock()
    request_context.__aexit__ = MagicMock()

    async def enter() -> MagicMock:
        return response

    async def exit(*args: object) -> None:
        return None

    request_context.__aenter__.side_effect = enter
    request_context.__aexit__.side_effect = exit
    response.text = MagicMock()

    async def response_text() -> str:
        return "payload"

    response.text.side_effect = response_text

    session = MagicMock()
    session.request.return_value = request_context
    client = _client(session)

    result = await client._request(
        "POST",
        "https://example.test/api",
        headers={"Authorization": "Bearer token"},
        params={"query": "value"},
        json_data={"key": "value"},
    )

    assert result == ApiResponse(
        status=200,
        text="payload",
        url="https://example.test/api",
    )
    session.request.assert_called_once()


@pytest.mark.asyncio
async def test_request_errors() -> None:
    session = MagicMock()
    client = _client(session)

    session.request.side_effect = TimeoutError
    with pytest.raises(TestApiError, match="timed out"):
        await client._request("GET", "https://example.test/timeout")

    session.request.side_effect = aiohttp.ClientError("network")
    with pytest.raises(TestApiError, match="failed: network"):
        await client._request("GET", "https://example.test/error")


def test_parse_json_response() -> None:
    client = _client()

    assert client._parse_json_response(
        ApiResponse(200, '{"value": 42}', "https://example.test/api")
    ) == {"value": 42}

    with pytest.raises(TestApiError, match="Invalid JSON"):
        client._parse_json_response(
            ApiResponse(200, "{invalid", "https://example.test/api")
        )

    with pytest.raises(TestApiError, match="Unexpected response type"):
        client._parse_json_response(
            ApiResponse(200, "[1, 2, 3]", "https://example.test/api")
        )
