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

        if data.get("error", {}).get("code") == 3 and retry:
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

        if data.get("error", {}).get("code") == 3 and retry:
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

    async def homestatus(self, home_id: str, *, force_refresh: bool = False) -> dict[str, Any]:
        """Return home status."""
        if self._status_cache is not None and not force_refresh:
            return self._status_cache

        data = await self._get(
            "homestatus",
            params={
                "home_id": home_id,
                "device_types": '["NLE"]',
            },
            base_url=SYNC_API_BASE,
        )

        self._status_cache = data
        return data

    async def contracts(self, home_id: str, *, force_refresh: bool = False) -> dict[str, Any]:
        """Return contracts."""
        if self._contracts_cache is not None and not force_refresh:
            return self._contracts_cache

        data = await self._post(
            "getcontracts",
            json_data={
                "home_id": home_id,
            },
        )

        self._contracts_cache = data
        return data

    async def discover_modules(self) -> dict[str, LegrandModule]:
        """Discover NLE child modules."""
        homesdata = await self.homesdata()

        modules: dict[str, LegrandModule] = {}

        for home in homesdata.get("body", {}).get("homes", []):
            for module in home.get("modules", []):
                if module.get("type") != "NLE":
                    continue

                if not module.get("bridge"):
                    continue

                modules[module["id"]] = LegrandModule(
                    id=module["id"],
                    name=module.get("name", module["id"]),
                    type=module.get("type", ""),
                    bridge=module.get("bridge"),
                )

        return modules

    async def update(self) -> dict[str, LegrandModule]:
        """Update data.

        For v0.1.0, this only exposes public API discovery data.
        Private gethomemeasure data is intentionally not used here.
        """
        return await self.discover_modules()


class LegrandPrivateApi:
    """Reserved for private gethomemeasure support."""