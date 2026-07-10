"""Private API client for Legrand Energy."""

from __future__ import annotations

import json
from typing import Any

import aiohttp
import logging

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
        """Initialize private API."""
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
        """GET helper."""
        url = f"{base_url}/{endpoint}"

        async with self._session.get(
            url,
            headers=self.headers,
            params=params,
            timeout=API_TIMEOUT,
        ) as response:
            data = await response.json(content_type=None)

        if response.status >= 400 or data.get("status") == "error" or "error" in data:
            raise LegrandPrivateApiError(data)

        return data

    async def homestatus(self, home_id: str) -> dict[str, Any]:
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
                "home": json.dumps(home_payload, separators=(",", ":")),
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
                "home": json.dumps(home_payload, separators=(",", ":")),
                "real_time": "true",
                "scale": "5min",
                "date_begin": date_begin,
                "date_end": date_end,
            },
        )
    
    async def getcontracts(self, home_id: str) -> dict[str, Any]:
        """Return private energy contracts."""
        return await self._get(
            APP_API_BASE,
            "getcontracts",
            params={"home_id": home_id},
            ),
        _LOGGER.error("Private API /getcontracts=%s", home_id)