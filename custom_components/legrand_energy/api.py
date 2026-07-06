"""API client for Legrand Energy."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import aiohttp

from .const import APP_API_BASE
from .models import ModuleMeasurement
from .parser import parse_gethomemeasure

_LOGGER = logging.getLogger(__name__)

REQUEST_TYPES = (
    "sum_energy_self_consumption",
    "sum_energy_buy_from_grid",
    "sum_energy_buy_from_grid$0",
    "sum_energy_buy_from_grid$1",
    "sum_energy_buy_from_grid$2",
    "sum_energy_buy_from_grid$3",
    "sum_energy_buy_from_grid$4",
    "sum_energy_buy_from_grid$5",
    "sum_energy_buy_from_grid$6",
    "sum_energy_buy_from_grid$7",
    "sum_energy_buy_from_grid$8",
    "sum_energy_buy_from_grid$9",
    "sum_energy_buy_from_grid$10",
    "sum_energy_buy_from_grid$11",
    "sum_energy_buy_from_grid_price$0",
    "sum_energy_buy_from_grid_price$1",
    "sum_energy_buy_from_grid_price$2",
    "sum_energy_buy_from_grid_price$3",
    "sum_energy_buy_from_grid_price$4",
    "sum_energy_buy_from_grid_price$5",
    "sum_energy_buy_from_grid_price$6",
    "sum_energy_buy_from_grid_price$7",
    "sum_energy_buy_from_grid_price$8",
    "sum_energy_buy_from_grid_price$9",
    "sum_energy_buy_from_grid_price$10",
    "sum_energy_buy_from_grid_price$11",
    "sum_energy_resell_to_grid",
    "sum_energy_self_consumption",
    "sum_energy_resell_to_grid_price",
    "sum_energy_elec",
    "sum_energy_elec$2",
    "sum_energy_elec$0",
    "sum_energy_elec$1",
    "sum_energy_price$0",
    "sum_energy_price$1",
    "sum_energy_price$2",
)


class LegrandEnergyApiError(Exception):
    """API error."""


class LegrandEnergyRateLimitError(LegrandEnergyApiError):
    """API rate limit error."""


class LegrandEnergyApi:
    """Legrand Energy API client."""

    def __init__(self, session: aiohttp.ClientSession, access_token: str) -> None:
        self._session = session
        self._access_token = access_token
        self._homes_cache: dict[str, Any] | None = None
        self._data_cache: dict[str, ModuleMeasurement] = {}

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"}

    async def update(self) -> dict[str, ModuleMeasurement]:
        """Update all measurements."""
        try:
            homesdata = self._homes_cache or await self.homesdata()
            home_payload = self._build_home_payload(homesdata)

            now = int(time.time())
            gethomemeasure = await self._get(
                "gethomemeasure",
                params={
                    "home": json.dumps(home_payload, separators=(",", ":")),
                    "real_time": "true",
                    "scale": "5min",
                    "date_begin": now - 24 * 3600,
                    "date_end": now,
                },
            )

            modules = parse_gethomemeasure(
                homesdata=homesdata,
                gethomemeasure=gethomemeasure,
                request_types=REQUEST_TYPES,
            )

            # Ignore bridge module without useful values.
            modules = {
                module_id: module
                for module_id, module in modules.items()
                if module.bridge is not None
            }

            self._data_cache = modules
            return modules

        except LegrandEnergyRateLimitError:
            if self._data_cache:
                _LOGGER.warning("Rate limit reached, returning cached data")
                return self._data_cache
            raise

    async def homesdata(self) -> dict[str, Any]:
        """Get homes data."""
        data = await self._get(
            "homesdata",
            params={
                "app_type": "app_magellan",
                "sync_measurements": "true",
                "gateway_types": json.dumps(["NLE"]),
            },
        )
        self._homes_cache = data
        return data

    def _build_home_payload(self, homesdata: dict[str, Any]) -> dict[str, Any]:
        """Build gethomemeasure home payload."""
        request_type = ",".join(REQUEST_TYPES)

        for home in homesdata.get("body", {}).get("homes", []):
            modules = []

            for module in home.get("modules", []):
                if module.get("type") != "NLE":
                    continue

                item = {
                    "id": module["id"],
                    "type": request_type,
                }

                if module.get("bridge"):
                    item["bridge"] = module["bridge"]

                modules.append(item)

            if modules:
                return {
                    "id": home["id"],
                    "modules": modules,
                    "rooms": [],
                }

        raise LegrandEnergyApiError("No NLE modules found")

    async def _get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """GET helper."""
        url = f"{APP_API_BASE}/{endpoint}"

        async with self._session.get(
            url,
            headers=self.headers,
            params=params,
        ) as response:
            data = await response.json(content_type=None)

            if response.status == 429 or data.get("error", {}).get("code") == 26:
                raise LegrandEnergyRateLimitError(data)

            if response.status >= 400 or data.get("status") == "error":
                raise LegrandEnergyApiError(data)

            return data