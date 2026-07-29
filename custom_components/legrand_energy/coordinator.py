"""Data update coordinator for Legrand Energy."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .api import (
    LegrandEnergyApi,
    LegrandEnergyApiError,
    LegrandEnergyAuthenticationError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .contract_service import ContractService
from .measurement_service import MeasurementService
from .models import (
    LegrandEnergyData,
    LegrandMeasurements,
    LegrandProjections,
)
from .models.contract import Contract
from .private_api import (
    LegrandPrivateApi,
    LegrandPrivateApiAuthenticationError,
    LegrandPrivateApiRateLimitError,
)
from .tariff_engine import TariffEngine, TariffState

_LOGGER = logging.getLogger(__name__)


class LegrandEnergyCoordinator(DataUpdateCoordinator[LegrandEnergyData]):
    """Coordinate Legrand Energy API updates."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: LegrandEnergyApi,
        private_api: LegrandPrivateApi | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

        self.api = api
        self._contract_service = (
            ContractService(private_api) if private_api is not None else None
        )
        self._measurement_service = (
            MeasurementService(private_api) if private_api is not None else None
        )

    async def _async_update_data(self) -> LegrandEnergyData:
        """Fetch and assemble the latest Legrand Energy data."""
        try:
            modules = await self.api.discover_modules()

            contract: Contract | None = None
            tariff: TariffState | None = None
            measurements: LegrandMeasurements | None = None
            measurements_by_module: dict[str, LegrandMeasurements] = {}
            projections: LegrandProjections | None = None

            home_id = self.api.get_first_home_id()

            if (
                self._contract_service is not None
                and self._measurement_service is not None
                and home_id is not None
            ):
                contract = await self._contract_service.async_get(home_id)
                tariff_engine = TariffEngine(contract) if contract is not None else None

                if tariff_engine is not None:
                    try:
                        tariff = tariff_engine.current_state(dt_util.now())
                    except ValueError as err:
                        _LOGGER.warning(
                            "Unable to determine current tariff: %s",
                            err,
                        )

                (
                    measurements,
                    measurements_by_module,
                    projections,
                ) = await self._measurement_service.async_get_all(
                    home_id=home_id,
                    modules=modules,
                    contract=contract,
                    tariff_engine=tariff_engine,
                    previous_data=self.data,
                )

            return LegrandEnergyData(
                modules=modules,
                contract=contract,
                tariff=tariff,
                measurements=measurements,
                measurements_by_module=measurements_by_module,
                projections=projections,
            )

        except LegrandPrivateApiRateLimitError as err:
            if self.data is not None:
                _LOGGER.debug("Netatmo API rate limit reached, keeping previous values")
                return self.data

            raise UpdateFailed("Netatmo API rate limit exceeded") from err

        except LegrandPrivateApiAuthenticationError as err:
            raise ConfigEntryAuthFailed(
                "Private Netatmo authentication expired"
            ) from err

        except LegrandEnergyAuthenticationError as err:
            raise ConfigEntryAuthFailed("Netatmo OAuth authentication expired") from err

        except LegrandEnergyApiError as err:
            raise UpdateFailed(f"Unable to update Legrand Energy data: {err}") from err
