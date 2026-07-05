"""Legrand / Netatmo API client for Home + Control."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session

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
    """Async API client using Home Assistant OAuth2 session."""

    def __init__(
        self,
        session: OAuth2Session,
        subscription_key: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self._session = session
        self._subscription_key = subscription_key
        self._timeout = timeout

    async def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generic GET request with OAuth2 token."""

        token = await self._session.async_get_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "ha-legrand-energy",
            "Ocp-Apim-Subscription-Key": self._subscription_key,
        }

        async with httpx.AsyncClient(
            base_url=API_ENDPOINT,
            timeout=self._timeout,
        ) as client:
            try:
                response = await client.get(
                    path,
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as err:
                _LOGGER.error(
                    "HTTP error calling %s: %s - %s",
                    path,
                    err.response.status_code,
                    err.response.text,
                )
                raise LegrandAPIError(str(err)) from err

            except httpx.RequestError as err:
                _LOGGER.error("Request error calling %s: %s", path, err)
                raise LegrandAPIError(str(err)) from err

    # -------------------------
    # Home + Control endpoints
    # -------------------------

    async def async_get_homesdata(self) -> dict[str, Any]:
        """Get list of homes."""
        return await self._get(ENDPOINT_HOMESDATA)

    async def async_get_hometopology(self, home_id: str) -> dict[str, Any]:
        """Get home topology (devices structure)."""
        return await self._get(ENDPOINT_HOMETOPOLOGY, {"home_id": home_id})

    async def async_get_homestatus(self, home_id: str) -> dict[str, Any]:
        """Get live home status."""
        return await self._get(ENDPOINT_HOMESTATUS, {"home_id": home_id})

    async def async_get_energy(self, home_id: str) -> dict[str, Any]:
        """Get energy consumption data."""
        return await self._get("/energy", {"home_id": home_id})
