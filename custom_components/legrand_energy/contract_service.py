"""Electricity contract retrieval service."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.util import dt as dt_util

from .contract_parser import parse_contract
from .models.contract import Contract
from .private_api import (
    LegrandPrivateApi,
    LegrandPrivateApiAuthenticationError,
    LegrandPrivateApiError,
    LegrandPrivateApiRateLimitError,
)

_LOGGER = logging.getLogger(__name__)

_CACHE_DURATION = timedelta(hours=1)


class ContractService:
    """Fetch and cache the electricity contract."""

    def __init__(self, private_api: LegrandPrivateApi) -> None:
        """Initialize the contract service."""
        self._private_api = private_api
        self._contract: Contract | None = None
        self._last_update: datetime | None = None

    async def async_get(self, home_id: str) -> Contract | None:
        """Return the cached contract and refresh it once per hour."""
        now = dt_util.now()

        cache_is_valid = (
            self._last_update is not None and now - self._last_update < _CACHE_DURATION
        )

        if cache_is_valid:
            return self._contract

        try:
            raw = await self._private_api.getcontracts(home_id)

        except (
            LegrandPrivateApiAuthenticationError,
            LegrandPrivateApiRateLimitError,
        ):
            raise

        except LegrandPrivateApiError as err:
            _LOGGER.warning(
                "Unable to update electricity contract, keeping cached data: %s",
                err,
            )
            return self._contract

        contract = parse_contract(raw)

        self._contract = contract
        self._last_update = now

        return contract
