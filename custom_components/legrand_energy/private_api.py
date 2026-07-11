"""Private API client for Legrand Energy."""

from __future__ import annotations

import json
import logging
from typing import Any, cast

import aiohttp

_LOGGER = logging.getLogger(__name__)

APP_API_BASE = "https://app.netatmo.net/api"
SYNC_API_BASE = "https://app.netatmo.net/syncapi/v1"

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
    """Legrand private API error."""


class LegrandPrivateApi:
    """Legrand private API client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        web_token: str,
    ) -> None:
        """Initialize the private API client."""
        self._session = session
        self._web_token = web_token

    @property
    def headers(self) -> dict[str, str]:
        """Return private API headers."""
        return {
            "Authorization": f"Bearer {self._web_token}",
            "Referer": "https://home.netatmo.com/",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0",
        }

    async def _get(
        self,
        base_url: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform a private API GET request."""
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        try:
            async with self._session.get(
                url,
                headers=self.headers,
                params=params,
                timeout=API_TIMEOUT,
            ) as response:
                status = response.status
                data = await response.json(content_type=None)

        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise LegrandPrivateApiError(
                f"Unable to fetch private API endpoint {endpoint}"
            ) from err

        if not isinstance(data, dict):
            raise LegrandPrivateApiError(
                f"Unexpected private API response type for {endpoint}"
            )

        if status >= 400:
            raise LegrandPrivateApiError(
                f"Private API request to {endpoint} failed with HTTP status {status}"
            )

        if data.get("status") == "error" or data.get("error") is not None:
            raise LegrandPrivateApiError(
                f"Private API returned an error for {endpoint}"
            )

        return cast(dict[str, Any], data)

    async def homestatus(
        self,
        home_id: str,
    ) -> dict[str, Any]:
        """Return private home status."""
        return await self._get(
            SYNC_API_BASE,
            "homestatus",
            params={
                "home_id": home_id,
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
        """Return electricity measures for one module."""
        home_payload = {
            "id": home_id,
            "modules": [
                {
                    "id": module_id,
                    "bridge": bridge,
                    "type": PRIVATE_MEASURE_TYPE_ELECTRICITY,
                }
            ],
            "rooms": [],
        }

        return await self._get(
            APP_API_BASE,
            "gethomemeasure",
            params={
                "home": json.dumps(
                    home_payload,
                    separators=(",", ":"),
                ),
                "real_time": "true",
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
        """Return electricity measures for multiple modules."""
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
            "rooms": [],
        }

        return await self._get(
            APP_API_BASE,
            "gethomemeasure",
            params={
                "home": json.dumps(
                    home_payload,
                    separators=(",", ":"),
                ),
                "real_time": "true",
                "scale": "5min",
                "date_begin": date_begin,
                "date_end": date_end,
            },
        )

    async def get_fluid_measure(
        self,
        home_id: str,
        module_id: str,
        bridge: str,
        date_begin: int,
        date_end: int,
    ) -> dict[str, Any]:
        """Return fluid measures for one module."""
        home_payload = {
            "id": home_id,
            "modules": [
                {
                    "id": module_id,
                    "bridge": bridge,
                    "type": PRIVATE_MEASURE_TYPE_FLUID,
                }
            ],
            "rooms": [],
        }

        return await self._get(
            APP_API_BASE,
            "gethomemeasure",
            params={
                "home": json.dumps(
                    home_payload,
                    separators=(",", ":"),
                ),
                "real_time": "true",
                "scale": "5min",
                "date_begin": date_begin,
                "date_end": date_end,
            },
        )

    async def getcontracts(
        self,
        home_id: str,
    ) -> dict[str, Any]:
        """Return private energy contracts."""
        _LOGGER.debug(
            "Fetching private energy contracts for home %s",
            home_id,
        )

        return await self._get(
            APP_API_BASE,
            "getcontracts",
            params={
                "home_id": home_id,
            },
        )
