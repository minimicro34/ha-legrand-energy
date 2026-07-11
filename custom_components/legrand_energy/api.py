"""API client for Legrand Energy."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import aiohttp

from .models import LegrandModule

_LOGGER = logging.getLogger(__name__)

APP_API_BASE = "https://app.netatmo.net/api"
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
    """Base exception for Legrand Energy API errors."""


class LegrandEnergyAuthenticationError(LegrandEnergyApiError):
    """Exception raised when authentication fails."""


class LegrandEnergyApi:
    """Client for the Legrand Energy APIs."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        access_token: str,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        token_update_callback: TokenUpdateCallback | None = None,
    ) -> None:
        """Initialize the Legrand Energy API client."""
        self._session = session
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_update_callback = token_update_callback

        self._homes_cache: dict[str, Any] | None = None

    @property
    def headers(self) -> dict[str, str]:
        """Return OAuth authorization headers."""
        return {"Authorization": f"Bearer {self._access_token}"}

    async def refresh_token(self) -> None:
        """Refresh the public Netatmo OAuth access token."""
        try:
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
                status = response.status
                data = await self._read_json_response(response)

        except (aiohttp.ClientError, TimeoutError) as err:
            raise LegrandEnergyAuthenticationError(
                "Unable to refresh the Netatmo OAuth token"
            ) from err

        access_token = data.get("access_token")

        if status >= 400 or not isinstance(access_token, str):
            raise LegrandEnergyAuthenticationError(
                f"OAuth token refresh failed with HTTP status {status}"
            )

        self._access_token = access_token

        refresh_token = data.get("refresh_token")
        if isinstance(refresh_token, str):
            self._refresh_token = refresh_token

        _LOGGER.debug("Legrand Energy OAuth token refreshed")

        if self._token_update_callback is not None:
            await self._token_update_callback(
                self._access_token,
                self._refresh_token,
            )

    async def _read_json_response(
        self,
        response: aiohttp.ClientResponse,
    ) -> dict[str, Any]:
        """Read and validate a JSON object response."""
        try:
            data = await response.json(content_type=None)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as err:
            raise LegrandEnergyApiError(
                f"Invalid JSON response from {response.url}"
            ) from err

        if not isinstance(data, dict):
            raise LegrandEnergyApiError(
                f"Unexpected response type from {response.url}: {type(data).__name__}"
            )

        return data

    @staticmethod
    def _get_error_code(data: dict[str, Any]) -> int | None:
        """Return the API error code when present."""
        error = data.get("error")

        if not isinstance(error, dict):
            return None

        code = error.get("code")

        if isinstance(code, int):
            return code

        if isinstance(code, str):
            try:
                return int(code)
            except ValueError:
                return None

        return None

    @staticmethod
    def _response_has_error(
        status: int,
        data: dict[str, Any],
    ) -> bool:
        """Return whether an API response represents an error."""
        return (
            status >= 400
            or data.get("status") == "error"
            or data.get("error") is not None
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
        """Perform a GET request."""
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        try:
            async with self._session.get(
                url,
                headers=headers if headers is not None else self.headers,
                params=params,
                timeout=API_TIMEOUT,
            ) as response:
                status = response.status
                data = await self._read_json_response(response)

        except LegrandEnergyApiError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise LegrandEnergyApiError(
                f"Unable to fetch API endpoint {endpoint}"
            ) from err

        error_code = self._get_error_code(data)

        # Only public OAuth requests can be retried by refreshing the
        # Netatmo OAuth token. Custom headers generally contain a private
        # web token that cannot be refreshed using the public OAuth flow.
        if error_code in (2, 3) and retry and headers is None:
            await self.refresh_token()

            return await self._get(
                endpoint,
                params=params,
                base_url=base_url,
                retry=False,
            )

        if self._response_has_error(status, data):
            if error_code in (2, 3):
                raise LegrandEnergyAuthenticationError(
                    f"Authentication failed for API endpoint {endpoint}"
                )

            raise LegrandEnergyApiError(
                f"GET request to {endpoint} failed with HTTP status {status}"
            )

        return data

    async def _post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        *,
        base_url: str = APP_API_BASE,
        retry: bool = True,
    ) -> dict[str, Any]:
        """Perform a POST request."""
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        try:
            async with self._session.post(
                url,
                headers={
                    **self.headers,
                    "Content-Type": "application/json",
                },
                json=json_data,
                timeout=API_TIMEOUT,
            ) as response:
                status = response.status
                data = await self._read_json_response(response)

        except LegrandEnergyApiError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise LegrandEnergyApiError(
                f"Unable to call API endpoint {endpoint}"
            ) from err

        error_code = self._get_error_code(data)

        if error_code in (2, 3) and retry:
            await self.refresh_token()

            return await self._post(
                endpoint,
                json_data=json_data,
                base_url=base_url,
                retry=False,
            )

        if self._response_has_error(status, data):
            if error_code in (2, 3):
                raise LegrandEnergyAuthenticationError(
                    f"Authentication failed for API endpoint {endpoint}"
                )

            raise LegrandEnergyApiError(
                f"POST request to {endpoint} failed with HTTP status {status}"
            )

        return data

    async def homesdata(
        self,
        *,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Return homes topology data."""
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
        """Return current home status."""
        return await self._get(
            "homestatus",
            params={
                "app_type": "app_magellan",
            },
        )

    async def contracts(self) -> dict[str, Any]:
        """Return energy contracts."""
        return await self._get(
            "getcontracts",
            params={
                "app_type": "app_magellan",
            },
        )

    async def discover_modules(
        self,
        *,
        force_refresh: bool = False,
    ) -> dict[str, LegrandModule]:
        """Discover available NLE modules."""
        homesdata = await self.homesdata(force_refresh=force_refresh)

        modules: dict[str, LegrandModule] = {}

        homes = homesdata.get("body", {}).get("homes", [])

        if not isinstance(homes, list):
            raise LegrandEnergyApiError(
                "Homes data response does not contain a valid homes list"
            )

        for home in homes:
            if not isinstance(home, dict):
                continue

            rooms_data = home.get("rooms", [])
            rooms: dict[str, str | None] = {}

            if isinstance(rooms_data, list):
                for room in rooms_data:
                    if not isinstance(room, dict):
                        continue

                    room_id = room.get("id")
                    if isinstance(room_id, str):
                        rooms[room_id] = room.get("name")

            home_modules = home.get("modules", [])
            if not isinstance(home_modules, list):
                continue

            for module in home_modules:
                if not isinstance(module, dict):
                    continue

                if module.get("type") != "NLE":
                    continue

                module_id = module.get("id")
                if not isinstance(module_id, str):
                    _LOGGER.debug("Ignoring NLE module without a valid ID")
                    continue

                module_name = module.get("name")
                if not isinstance(module_name, str) or not module_name:
                    module_name = module_id

                module_type = module.get("type")
                if not isinstance(module_type, str):
                    module_type = ""

                room_id = module.get("room_id")
                room_name = rooms.get(room_id) if isinstance(room_id, str) else None

                modules[module_id] = LegrandModule(
                    id=module_id,
                    name=module_name,
                    type=module_type,
                    bridge=module.get("bridge"),
                    room=room_name,
                    setup_date=module.get("setup_date"),
                )

        return modules

    async def update(self) -> dict[str, LegrandModule]:
        """Discover and return available Legrand modules."""
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
        """Return private energy measurements for a home module."""
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
            headers={
                "Authorization": f"Bearer {web_token}",
                "Referer": "https://home.netatmo.com/",
                "Accept": "application/json, text/plain, */*",
            },
            retry=False,
        )
