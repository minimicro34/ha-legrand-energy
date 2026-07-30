"""Module discovery service for Legrand Energy."""

from __future__ import annotations

from .api import LegrandEnergyApi
from .models import LegrandModule


class ModuleService:
    """Retrieve Legrand Energy modules."""

    def __init__(self, api: LegrandEnergyApi) -> None:
        """Initialize the module service."""
        self._api = api

    async def async_get(self) -> dict[str, LegrandModule]:
        """Return discovered Legrand Energy modules."""
        modules: dict[str, LegrandModule] = await self._api.discover_modules()
        return modules
