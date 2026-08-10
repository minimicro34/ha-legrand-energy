"""Private API client for Legrand Energy."""

from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

from .authentication import AuthenticationManager
from .base_api import BaseApiClient
from .helpers.fluid_types import private_measure_type
from .models.fluid import FluidType
from .services.private import (
    PrivateAuthServiceAuthenticationError,
    PrivateAuthServiceError,
)

_LOGGER = logging.getLogger(__name__)

APP_API_BASE = "https://app.netatmo.net/api"


class LegrandPrivateApiError(Exception):
    """Base private API error."""


class LegrandPrivateApiAuthenticationError(LegrandPrivateApiError):
    """Private API authentication error."""


class LegrandPrivateApiRateLimitError(LegrandPrivateApiError):
    """Private API rate limit exceeded."""


class LegrandPrivateApi(BaseApiClient):
    """Client for the private Netatmo API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        authentication: AuthenticationManager,
    ) -> None:
        """Initialize the private API client."""
        super().__init__(session, LegrandPrivateApiError)
        self._authentication = authentication

    @property
    def web_token(self) -> str:
        """Return the current private web token."""
        return self._authentication.private.web_token

    def _headers(self) -> dict[str, str]:
        """Return private API request headers."""
        return self._authentication.private_headers

    async def _get(
        self,
        base_url: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        retry_auth: bool = True,
    ) -> dict[str, Any]:
        """Perform a private API GET request."""
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        response = await self._request(
            "GET",
            url,
            headers=self._headers(),
            params=params,
        )

        if response.status in (401, 403):
            _LOGGER.info(
                "Private API returned %s for %s, attempting authentication refresh",
                response.status,
                endpoint,
            )

            if retry_auth:
                await self.refresh_web_token()

                return await self._get(
                    base_url,
                    endpoint,
                    params,
                    retry_auth=False,
                )

            raise LegrandPrivateApiAuthenticationError(
                f"Private API request to {endpoint} failed with "
                f"HTTP status {response.status} "
                "after authentication refresh"
            )

        if response.status == 429:
            raise LegrandPrivateApiRateLimitError(
                f"Private API rate limit exceeded for {endpoint}: {response.text[:300]}"
            )

        if response.status >= 400:
            raise LegrandPrivateApiError(
                f"Private API request to {endpoint} "
                f"failed with HTTP status {response.status}: "
                f"{response.text[:300]}"
            )

        data = self._parse_json_response(response)

        if data.get("status") == "error":
            raise LegrandPrivateApiError(
                f"Private API request to {endpoint} "
                f"returned an API error: {data.get('error')}"
            )

        return data

    async def homestatus(self, home_id: str) -> dict[str, Any]:
        """Return the current private home status."""
        return await self._get(
            APP_API_BASE,
            "homestatus",
            {"home_id": home_id},
        )

    async def get_home_measure(
        self,
        *,
        home: dict[str, Any],
        scale: str = "5min",
        real_time: bool = True,
        date_begin: int | None = None,
        date_end: int | None = None,
    ) -> dict[str, Any]:
        """Return historical or real-time measurements."""

        params: dict[str, Any] = {
            "home": json.dumps(home, separators=(",", ":")),
            "real_time": str(real_time).lower(),
            "scale": scale,
        }

        if date_begin is not None:
            params["date_begin"] = date_begin

        if date_end is not None:
            params["date_end"] = date_end

        return await self._get(
            APP_API_BASE,
            "gethomemeasure",
            params,
        )

    async def get_measure(
        self,
        home_id: str,
        module_id: str,
        measure_type: str,
        bridge: str | None = None,
    ) -> dict[str, Any]:
        """Fetch a raw private measure for testing."""
        module_payload: dict[str, Any] = {
            "id": module_id,
            "type": measure_type,
        }

        if bridge is not None:
            module_payload["bridge"] = bridge

        home_payload = {
            "id": home_id,
            "modules": [module_payload],
        }

        return await self._get(
            APP_API_BASE,
            "gethomemeasure",
            {
                "home": json.dumps(home_payload),
                "scale": "max",
                "date_end": "last",
            },
        )

    async def get_electricity_measure(
        self,
        home_id: str,
        module_id: str,
        bridge: str,
        date_begin: int,
        date_end: int,
    ) -> dict[str, Any]:
        """Return electricity measurements for one module."""
        home_payload = {
            "id": home_id,
            "modules": [
                {
                    "id": module_id,
                    "bridge": bridge,
                    "type": private_measure_type(FluidType.ELECTRICITY),
                },
            ],
        }

        return await self._get(
            APP_API_BASE,
            "gethomemeasure",
            {
                "home": json.dumps(home_payload),
                "scale": "5min",
                "date_begin": date_begin,
                "date_end": date_end,
            },
        )

    async def get_fluid_measures(
        self,
        home_id: str,
        modules: list[tuple[str, str]],
        fluid_type: FluidType,
        date_begin: int,
        date_end: int,
        scale: str = "5min",
    ) -> dict[str, Any]:
        """Return measurements for multiple modules of one fluid type."""
        measure_type = private_measure_type(fluid_type)

        home_payload = {
            "id": home_id,
            "modules": [
                {
                    "id": module_id,
                    "bridge": bridge,
                    "type": measure_type,
                }
                for module_id, bridge in modules
            ],
        }

        return await self._get(
            APP_API_BASE,
            "gethomemeasure",
            {
                "home": json.dumps(home_payload),
                "scale": scale,
                "date_begin": date_begin,
                "date_end": date_end,
            },
        )

    async def get_electricity_measures(
        self,
        home_id: str,
        modules: list[tuple[str, str]],
        date_begin: int,
        date_end: int,
        scale: str = "5min",
    ) -> dict[str, Any]:
        """Return electricity measurements for multiple modules."""
        return await self.get_fluid_measures(
            home_id=home_id,
            modules=modules,
            fluid_type=FluidType.ELECTRICITY,
            date_begin=date_begin,
            date_end=date_end,
            scale=scale,
        )

    async def getcontracts(self, home_id: str) -> dict[str, Any]:
        """Return the electricity contract."""
        return await self._get(
            APP_API_BASE,
            "getcontracts",
            {"home_id": home_id},
        )

    async def refresh_web_token(self) -> str:
        """Refresh the Netatmo private web access token."""

        try:
            session = await self._authentication.refresh_private()

        except PrivateAuthServiceAuthenticationError as err:
            raise LegrandPrivateApiAuthenticationError(
                f"Unable to refresh private Netatmo authentication: {err}"
            ) from err
        except PrivateAuthServiceError as err:
            raise LegrandPrivateApiError(
                f"Unable to refresh private Netatmo session: {err}"
            ) from err

        return session.web_token
