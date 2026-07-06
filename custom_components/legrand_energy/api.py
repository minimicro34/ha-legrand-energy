"""API client for Legrand Energy / Netatmo Energy."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import API_BASE

_LOGGER = logging.getLogger(__name__)


class LegrandEnergyApiError(Exception):
    """Raised when the Legrand Energy API returns an error."""


class LegrandEnergyApi:
    """Small async client for Netatmo Energy API."""

    def __init__(self, session: aiohttp.ClientSession, access_token: str) -> None:
        self._session = session
        self._access_token = access_token

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"}

    async def homesdata(self) -> dict[str, Any]:
        """Return homes data."""
        return await self._post("homesdata")

    async def homestatus(self, home_id: str) -> dict[str, Any]:
        """Return home status."""
        return await self._post("homestatus", data={"home_id": home_id})

    async def getmeasure(
        self,
        device_id: str,
        module_id: str,
        measure_type: str = "sum_energy_buy_from_grid",
        scale: str = "1day",
        date_end: str = "last",
        limit: int = 1,
    ) -> Any:
        """Return a measurement for a module."""
        params = {
            "device_id": device_id,
            "module_id": module_id,
            "scale": scale,
            "type": measure_type,
            "date_end": date_end,
            "limit": limit,
        }

        data = await self._get("getmeasure", params=params)
        body = data.get("body", [])

        if not body:
            return None

        try:
            return body[-1]["value"][-1][0]
        except (KeyError, IndexError, TypeError):
            return None

    async def discover_nle_modules(self) -> dict[str, Any]:
        """Discover NLE / Drivia modules."""
        data = await self.homesdata()
        homes = data.get("body", {}).get("homes", [])

        discovered: dict[str, Any] = {
            "homes": [],
            "modules": [],
        }

        for home in homes:
            home_id = home.get("id")
            home_name = home.get("name")
            modules = home.get("modules", [])

            for module in modules:
                if module.get("type") != "NLE":
                    continue

                module_id = module.get("id")
                bridge = module.get("bridge")
                name = module.get("name", module_id)

                discovered["modules"].append(
                    {
                        "home_id": home_id,
                        "home_name": home_name,
                        "id": module_id,
                        "name": name,
                        "type": module.get("type"),
                        "bridge": bridge,
                        "is_bridge": bridge is None,
                    }
                )

            discovered["homes"].append(
                {
                    "id": home_id,
                    "name": home_name,
                }
            )

        return discovered

    async def async_get_all_measurements(self) -> dict[str, Any]:
        """Return measurements for all discovered NLE child modules."""
        discovered = await self.discover_nle_modules()

        results: dict[str, Any] = {
            "homes": discovered["homes"],
            "modules": {},
        }

        bridge_id: str | None = None

        for module in discovered["modules"]:
            if module["is_bridge"]:
                bridge_id = module["id"]
                break

        if bridge_id is None:
            _LOGGER.warning("No NLE bridge found")
            return results

        for module in discovered["modules"]:
            if module["is_bridge"]:
                continue

            if module.get("name") != "Total":
                continue

            module_id = module["id"]

            value = await self.getmeasure(
                device_id=bridge_id,
                module_id=module_id,
                measure_type="sum_energy_buy_from_grid",
                scale="1day",
                date_end="last",
                limit=1,
            )

            results["modules"][module_id] = {
                **module,
                "energy": value,
            }

        return results

    async def _post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{API_BASE}/{endpoint}"

        async with self._session.post(
            url,
            headers=self.headers,
            data=data,
        ) as response:
            result = await response.json(content_type=None)

            if response.status >= 400 or result.get("status") == "error":
                raise LegrandEnergyApiError(result)

            return result
        data = await self._get("getmeasure", params=params)
        _LOGGER.warning("GETMEASURE %s %s = %s", module_id, measure_type, data)

        body = data.get("body", [])

        if not body:
            return None

        try:
            return body[-1]["value"][-1][0]
        except (KeyError, IndexError, TypeError):
            return None