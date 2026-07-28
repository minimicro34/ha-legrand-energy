"""API client for Legrand Energy."""

from __future__ import annotations

import json
from typing import Any

import aiohttp

from .authentication import AuthenticationManager
from .base_api import BaseApiClient
from .models import LegrandModule

APP_API_BASE = "https://app.netatmo.net/api"


PRIVATE_MEASURE_TYPE_ELECTRICITY = (
    "sum_energy_elec,"
    "sum_energy_elec$0,"
    "sum_energy_elec$1,"
    "sum_energy_elec$2,"
    "sum_energy_price$0,"
    "sum_energy_price$1,"
    "sum_energy_price$2"
)


class LegrandEnergyApiError(Exception):
    """Base exception for Legrand Energy API errors."""


class LegrandEnergyAuthenticationError(LegrandEnergyApiError):
    """Exception raised when authentication fails."""


class LegrandEnergyApi(BaseApiClient):
    """Client for the Legrand Energy APIs."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        authentication: AuthenticationManager,
    ) -> None:
        """Initialize the Legrand Energy API client."""
        super().__init__(session, LegrandEnergyApiError)
        self._authentication = authentication
        self._homes_cache: dict[str, Any] | None = None

    @property
    def headers(self) -> dict[str, str]:
        """Return OAuth authorization headers."""
        return self._authentication.authorization_headers

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

        response = await self._request(
            "GET",
            url,
            headers=headers if headers is not None else self.headers,
            params=params,
        )
        status = response.status
        data = self._parse_json_response(response)

        error_code = self._get_error_code(data)

        if error_code in (2, 3) and retry and headers is None:
            try:
                await self._authentication.refresh_oauth()
            except Exception as err:
                raise LegrandEnergyAuthenticationError(
                    "Unable to refresh the Netatmo OAuth token"
                ) from err

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

        response = await self._request(
            "POST",
            url,
            headers={
                **self.headers,
                "Content-Type": "application/json",
            },
            json_data=json_data,
        )
        status = response.status
        data = self._parse_json_response(response)

        error_code = self._get_error_code(data)

        if error_code in (2, 3) and retry:
            try:
                await self._authentication.refresh_oauth()
            except Exception as err:
                raise LegrandEnergyAuthenticationError(
                    "Unable to refresh the Netatmo OAuth token"
                ) from err

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
                        room_name = room.get("name")
                        rooms[room_id] = (
                            room_name if isinstance(room_name, str) else None
                        )

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
                    continue

                module_name = module.get("name")
                if not isinstance(module_name, str) or not module_name:
                    module_name = module_id

                module_type = module.get("type")
                if not isinstance(module_type, str):
                    module_type = ""

                room_id = module.get("room_id")
                room_name = rooms.get(room_id) if isinstance(room_id, str) else None

                bridge = module.get("bridge")
                setup_date = module.get("setup_date")

                modules[module_id] = LegrandModule(
                    id=module_id,
                    name=module_name,
                    type=module_type,
                    bridge=bridge if isinstance(bridge, str) else None,
                    room=room_name,
                    setup_date=(setup_date if isinstance(setup_date, int) else None),
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
