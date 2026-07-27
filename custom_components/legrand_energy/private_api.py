"""Private API client for Legrand Energy."""

from __future__ import annotations

import json
import logging
from typing import Any, cast

import aiohttp

from .authentication import AuthenticationManager
from .services.private import (
    PrivateAuthServiceAuthenticationError,
    PrivateAuthServiceError,
)

_LOGGER = logging.getLogger(__name__)

APP_API_BASE = "https://app.netatmo.net/api"

API_TIMEOUT = aiohttp.ClientTimeout(total=30)

PRIVATE_MEASURE_TYPE_ELECTRICITY = (
    "sum_energy_elec,"
    "sum_energy_elec$0,"
    "sum_energy_elec$1,"
    "sum_energy_elec$2,"
    "sum_energy_price$0,"
    "sum_energy_price$1,"
    "sum_energy_price$2"
)

PRIVATE_MEASURE_TYPE_FLUID = "sum_fluid_consumption$0,sum_fluid_price$0"


class LegrandPrivateApiError(Exception):
    """Base private API error."""


class LegrandPrivateApiAuthenticationError(LegrandPrivateApiError):
    """Private API authentication error."""


class LegrandPrivateApiRateLimitError(LegrandPrivateApiError):
    """Private API rate limit exceeded."""


class LegrandPrivateApi:
    """Client for the private Netatmo API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        authentication: AuthenticationManager,
    ) -> None:
        """Initialize the private API client."""
        self._session = session
        self._authentication = authentication

    @property
    def web_token(self) -> str:
        """Return the current private web token."""
        return self._authentication.private.web_token

    def _headers(self) -> dict[str, str]:
        """Return private API request headers."""
        return self._authentication.private_headers

    def _can_refresh(self) -> bool:
        """Return whether private authentication data is available."""
        return bool(self._authentication.private.cookies)

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

        try:
            async with self._session.get(
                url,
                headers=self._headers(),
                params=params,
                timeout=API_TIMEOUT,
            ) as response:
                if response.status in (401, 403):
                    if retry_auth and self._can_refresh():
                        await self.refresh_web_token()

                        return await self._get(
                            base_url,
                            endpoint,
                            params,
                            retry_auth=False,
                        )

                    raise LegrandPrivateApiAuthenticationError(
                        f"Private API request to {endpoint} "
                        f"failed with HTTP status {response.status}"
                    )

                if response.status == 429:
                    response_text = await response.text()

                    raise LegrandPrivateApiRateLimitError(
                        f"Private API rate limit exceeded for {endpoint}: "
                        f"{response_text[:300]}"
                    )

                if response.status >= 400:
                    response_text = await response.text()

                    raise LegrandPrivateApiError(
                        f"Private API request to {endpoint} "
                        f"failed with HTTP status {response.status}: "
                        f"{response_text[:300]}"
                    )

                try:
                    data = await response.json(content_type=None)
                except (
                    aiohttp.ContentTypeError,
                    json.JSONDecodeError,
                ) as err:
                    raise LegrandPrivateApiError(
                        f"Private API request to {endpoint} returned invalid JSON"
                    ) from err

        except LegrandPrivateApiError:
            raise

        except TimeoutError as err:
            raise LegrandPrivateApiError(
                f"Private API request to {endpoint} timed out"
            ) from err

        except aiohttp.ClientError as err:
            raise LegrandPrivateApiError(
                f"Private API request to {endpoint} failed: {err}"
            ) from err

        if not isinstance(data, dict):
            raise LegrandPrivateApiError(
                f"Private API request to {endpoint} returned an unexpected response"
            )

        if data.get("status") == "error":
            raise LegrandPrivateApiError(
                f"Private API request to {endpoint} "
                f"returned an API error: {data.get('error')}"
            )

        return cast(dict[str, Any], data)

    async def homestatus(self, home_id: str) -> dict[str, Any]:
        """Return the current private home status."""
        return await self._get(
            APP_API_BASE,
            "homestatus",
            {"home_id": home_id},
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
                    "type": PRIVATE_MEASURE_TYPE_ELECTRICITY,
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

    async def get_electricity_measures(
        self,
        home_id: str,
        modules: list[tuple[str, str]],
        date_begin: int,
        date_end: int,
    ) -> dict[str, Any]:
        """Return electricity measurements for multiple modules."""
        home_payload = {
            "id": home_id,
            "modules": [
                {
                    "id": module_id,
                    "bridge": bridge,
                    "type": PRIVATE_MEASURE_TYPE_ELECTRICITY,
                }
                for module_id, bridge in modules
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

    async def getcontracts(self, home_id: str) -> dict[str, Any]:
        """Return the electricity contract."""
        return await self._get(
            APP_API_BASE,
            "getcontracts",
            {"home_id": home_id},
        )

    async def refresh_web_token(self) -> str:
        """Refresh the Netatmo private web access token."""
        _LOGGER.debug("Refreshing Netatmo private web token")

        try:
            session = await self._authentication.refresh_private()

        except PrivateAuthServiceAuthenticationError as err:
            raise LegrandPrivateApiAuthenticationError(str(err)) from err

        except PrivateAuthServiceError as err:
            raise LegrandPrivateApiError(str(err)) from err

        _LOGGER.debug("Netatmo private web token refreshed successfully")

        return session.web_token
