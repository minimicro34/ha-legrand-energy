"""Legrand / Netatmo API client for Home + Control."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .const import (
    API_ENDPOINT,
    DEFAULT_TIMEOUT,
    ENDPOINT_HOMESDATA,
    ENDPOINT_HOMESTATUS,
    ENDPOINT_HOMETOPOLOGY,
)

_LOGGER = logging.getLogger(__name__)


class LegrandAPIError(Exception):
    """Generic API error."""


class LegrandAPI:
    """Simple async API client for Netatmo Home + Control."""

    def __init__(
        self,
        access_token: str,
        subscription_key: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self._access_token = access_token
        self._subscription_key = subscription_key
        self._timeout = timeout

        self._client = httpx.AsyncClient(
            base_url=API_ENDPOINT,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "User-Agent": "ha-legrand-energy",
                "Ocp-Apim-Subscription-Key": subscription_key,
            },
        )

    async def async_close(self) -> None:
        """Close HTTP client."""
        await self._client.aclose()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Generic GET request."""
        try:
            response = await self._client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as err:
            _LOGGER.error("API request failed: %s", err)
            raise LegrandAPIError(str(err)) from err

    # -------------------------
    # Home + Control endpoints
    # -------------------------

    async def async_get_homesdata(self) -> dict[str, Any]:
        """Get homes list."""
        return await self._get(ENDPOINT_HOMESDATA)

    async def async_get_hometopology(self, home_id: str) -> dict[str, Any]:
        """Get home topology."""
        return await self._get(ENDPOINT_HOMETOPOLOGY, {"home_id": home_id})

    async def async_get_homestatus(self, home_id: str) -> dict[str, Any]:
        """Get home status (live data)."""
        return await self._get(ENDPOINT_HOMESTATUS, {"home_id": home_id})

    # -------------------------
    # Energy (meter.read)
    # -------------------------

    async def async_get_energy(self, home_id: str) -> dict[str, Any]:
        """Get energy data for home."""
        return await self._get("/energy", {"home_id": home_id})
