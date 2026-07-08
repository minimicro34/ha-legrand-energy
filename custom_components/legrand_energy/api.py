"""API client for Legrand Energy."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

import aiohttp

from .models import LegrandModule

_LOGGER = logging.getLogger(__name__)

APP_API_BASE = "https://app.netatmo.net/api"
SYNC_API_BASE = "https://app.netatmo.net/syncapi/v1"
TOKEN_URL = "https://api.netatmo.com/oauth2/token"

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

TokenUpdateCallback = Callable[[str, str], Awaitable[None]]


class LegrandEnergyApiError(Exception):
    """Legrand Energy API error."""


class LegrandEnergyApi:
    """Legrand Energy public API client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        access_token: str,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        token_update_callback: TokenUpdateCallback | None = None,
    ) -> None:
        self._session = session
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_update_callback = token_update_callback

        self._homes_cache: dict[str, Any] | None = None
        self._status_cache: dict[str, Any] | None = None
        self._contracts_cache: dict[str, Any] | None = None

    @property
    def headers(self) -> dict[str, str]:
        """Return authorization headers."""
        return {"Authorization": f"Bearer {self._access_token}"}

    async def refresh_token(self) -> None:
        """Refresh OAuth token."""
        async with self._session.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            timeout=API_TIMEOUT,
        ) as response:
            data = await response.json(content_type=None)

        if response.status >= 400 or "access_token" not in data:
            raise LegrandEnergyApiError(data)

        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token", self._refresh_token)

        _LOGGER.info("Legrand Energy OAuth token refreshed")

        if self._token_update_callback is not None:
            await self._token_update_callback(
                self._access_token,
                self._refresh_token,
            )

    async def _get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        base_url: str = APP_API_BASE,
        retry: bool = True,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """GET helper."""
        url = f"{base_url}/{endpoint}"

        async with self._session.get(
            url,
            headers=headers or self.headers,
            params=params,
            timeout=API_TIMEOUT,
        ) as response:
            data = await response.json(content_type=None)

        if data.get("error", {}).get("code") in (2, 3) and retry:
            await self.refresh_token()
            return await self._get(
                endpoint,
                params=params,
                base_url=base_url,
                retry=False,
            )

        if response.status >= 400 or data.get("status") == "error" or "error" in data:
            _LOGGER.debug("Legrand API %s returned %s", endpoint, data)
            raise LegrandEnergyApiError(data)

        return data

    async def _post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        *,
        base_url: str = APP_API_BASE,
        retry: bool = True,
    ) -> dict[str, Any]:
        """POST helper."""
        url = f"{base_url}/{endpoint}"

        async with self._session.post(
            url,
            headers={
                **self.headers,
                "Content-Type": "application/json",
            },
            json=json_data,
            timeout=API_TIMEOUT,
        ) as response:
            data = await response.json(content_type=None)

        if data.get("error", {}).get("code") in (2, 3) and retry:
            await self.refresh_token()
            return await self._post(
                endpoint,
                json_data=json_data,
                base_url=base_url,
                retry=False,
            )

        if response.status >= 400 or data.get("status") == "error" or "error" in data:
            _LOGGER.debug("Legrand API POST %s returned %s", endpoint, data)
            raise LegrandEnergyApiError(data)

        return data

    async def homesdata(self, *, force_refresh: bool = False) -> dict[str, Any]:
        """Return homes data."""
        if self._homes_cache is not None and not force_refresh:
            return self._homes_cache

        data = await self._get(
            "homesdata",
            params={
                "app_type": "app_magellan",
                "sync_measurements": "true",
                "gateway_types": '["NLE"]',
            },
        )

        self._homes_cache = data
        return data
    
    async def homestatus(self) -> dict[str, Any]:
        """Return home status."""
        return await self._get(
            "homestatus",
            params={
                "app_type": "app_magellan",
            },
        )

    async def contracts(self) -> dict[str, Any]:
        """Return contracts."""
        return await self._get(
            "getcontracts",
            params={
                "app_type": "app_magellan",
            },
        )

    async def discover_modules(self) -> dict[str, LegrandModule]:
        """Discover NLE modules."""
        homesdata = await self.homesdata()

        modules: dict[str, LegrandModule] = {}

        for home in homesdata.get("body", {}).get("homes", []):
            # Dictionnaire des pièces
            rooms = {
                room["id"]: room.get("name")
                for room in home.get("rooms", [])
            }

            # Modules
            for module in home.get("modules", []):
                if module.get("type") != "NLE":
                    continue

                modules[module["id"]] = LegrandModule(
                    id=module["id"],
                    name=module.get("name", module["id"]),
                    type=module.get("type", ""),
                    bridge=module.get("bridge"),
                    room=rooms.get(module.get("room_id")),
                    setup_date=module.get("setup_date"),
                )

        return modules

    async def update(self) -> dict[str, LegrandModule]:
        """Update data.

        For v0.1.0, this only exposes public API discovery data.
        Private gethomemeasure data is intentionally not used here.
        """
        return await self.discover_modules()

    async def get_home_measure(
    self,
    home_id: str,
    module_id: str,
    bridge: str,
    web_token: str,
    date_begin: int,
    date_end: int,
) -> dict[str, Any]:
        """Return private home measures."""
        return await self._get(
            "gethomemeasure",
            params={
                "home": (
                    '{"id":"'
                    + home_id
                    + '","modules":[{"id":"'
                    + module_id
                    + '","bridge":"'
                    + bridge
                    + '","type":"'
                    + PRIVATE_MEASURE_TYPE_ELECTRICITY
                    + '"}],"rooms":[]}'
                ),
                "real_time": "true",
                "scale": "5min",
                "date_begin": date_begin,
                "date_end": date_end,
            },
            headers={
                "Authorization": f"Bearer {web_token}",
                "Referer": "https://home.netatmo.com/",
                "Accept": "application/json, text/plain, */*",
            },
        )