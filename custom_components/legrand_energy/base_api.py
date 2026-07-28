"""Shared HTTP helpers for Legrand Energy API clients."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import aiohttp

API_TIMEOUT = aiohttp.ClientTimeout(total=30)


@dataclass(frozen=True, slots=True)
class ApiResponse:
    """Raw HTTP response used by API clients."""

    status: int
    text: str
    url: str


class BaseApiClient:
    """Base client providing shared HTTP and JSON handling."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        error_type: type[Exception],
    ) -> None:
        """Initialize the base API client."""
        self._session = session
        self._error_type = error_type

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> ApiResponse:
        """Perform an HTTP request and return its raw response."""
        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=API_TIMEOUT,
            ) as response:
                return ApiResponse(
                    status=response.status,
                    text=await response.text(),
                    url=str(response.url),
                )

        except TimeoutError as err:
            raise self._error_type(f"Request to {url} timed out") from err

        except aiohttp.ClientError as err:
            raise self._error_type(f"Request to {url} failed: {err}") from err

    def _parse_json_response(
        self,
        response: ApiResponse,
    ) -> dict[str, Any]:
        """Decode and validate a JSON object response."""
        try:
            data = json.loads(response.text)
        except (json.JSONDecodeError, UnicodeDecodeError) as err:
            raise self._error_type(
                f"Invalid JSON response from {response.url}"
            ) from err

        if not isinstance(data, dict):
            raise self._error_type(
                f"Unexpected response type from {response.url}: {type(data).__name__}"
            )

        return data
