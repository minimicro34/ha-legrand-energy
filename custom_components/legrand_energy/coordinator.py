"""Data update coordinator for Legrand Energy."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

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
    FluidMeasurements,
    LegrandEnergyData,
    LegrandMeasurements,
    LegrandProjections,
)
from .models.contract import Contract
from .module_service import ModuleService
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
        self.private_api = private_api
        self._module_service = ModuleService(api)

        self._contract_service = (
            ContractService(private_api) if private_api is not None else None
        )
        self._measurement_service = (
            MeasurementService(private_api) if private_api is not None else None
        )

    async def async_debug_homestatus(self) -> None:
        """Log a sanitized summary of the private Home + Control status."""
        if self.private_api is None:
            _LOGGER.warning("Private Home + Control API is unavailable")
            return

        home_id = self.api.get_first_home_id()
        if home_id is None:
            _LOGGER.warning("Unable to probe Home + Control status: no home found")
            return

        payload = await self.private_api.homestatus(home_id)
        interesting = ("power", "current", "energy", "consumption", "measure", "load")
        matches: list[str] = []
        module_types: set[str] = set()

        def walk(value: object, path: str = "root") -> None:
            if isinstance(value, dict):
                module_type = value.get("type")
                if isinstance(module_type, str):
                    module_types.add(module_type)

                for key, child in value.items():
                    child_path = f"{path}.{key}"
                    if any(term in key.lower() for term in interesting):
                        if isinstance(child, (str, int, float, bool)) or child is None:
                            matches.append(f"{child_path}={child!r}")
                        else:
                            matches.append(f"{child_path}=<{type(child).__name__}>")
                    walk(child, child_path)
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    walk(child, f"{path}[{index}]")

        walk(payload)

        _LOGGER.warning(
            "Legrand Energy homestatus probe: module_types=%s; matching_fields=%s",
            sorted(module_types),
            matches or ["<none>"],
        )

    async def async_debug_historical_availability(self) -> None:
        """Probe yearly electricity availability without changing Recorder."""
        if self.private_api is None:
            _LOGGER.warning("Legrand historical probe: private API unavailable")
            return
        home_id = self.api.get_first_home_id()
        if home_id is None:
            _LOGGER.warning("Legrand historical probe: no home found")
            return
        modules = await self._module_service.async_get()
        from .helpers.private_measure_decoder import decode_points_by_module
        from .models.fluid import FluidType

        electricity = [
            (module.id, module.bridge)
            for module in modules.values()
            if module.bridge is not None and module.fluid_type is FluidType.ELECTRICITY
        ]
        if not electricity:
            _LOGGER.warning("Legrand historical probe: no electricity modules")
            return
        # One year per call, including 2022 and early 2026. No raw payload,
        # module identifiers, authentication details or household data logged.
        for year in range(2022, 2027):
            start = int(datetime(year, 1, 1, tzinfo=UTC).timestamp())
            stop = int(datetime(year + 1, 1, 1, tzinfo=UTC).timestamp()) - 1
            try:
                payload = await self.private_api.get_fluid_measures(
                    home_id=home_id,
                    modules=electricity,
                    fluid_type=FluidType.ELECTRICITY,
                    date_begin=start,
                    date_end=stop,
                    scale="1day",
                )
                decoded = decode_points_by_module(
                    payload, fluid_type=FluidType.ELECTRICITY
                )
                points = [point for series in decoded.values() for point in series]
                dates = [point.timestamp for point in points]
                _LOGGER.warning(
                    "Legrand historical probe %s: modules=%s points=%s "
                    "first=%s last=%s",
                    year,
                    len(decoded),
                    len(points),
                    min(dates).isoformat() if dates else "none",
                    max(dates).isoformat() if dates else "none",
                )
            except LegrandPrivateApiRateLimitError:
                _LOGGER.warning(
                    "Legrand historical probe: rate limited in %s; stopping", year
                )
                break
            except Exception as err:
                _LOGGER.warning(
                    "Legrand historical probe %s: %s: %s",
                    year,
                    type(err).__name__,
                    str(err)[:180],
                )
                # Do not continue if authentication has failed.
                if isinstance(err, LegrandPrivateApiAuthenticationError):
                    break

    async def async_debug_historical_months(self) -> None:
        """Probe older measurements by month, without writing to Recorder."""
        if self.private_api is None:
            _LOGGER.warning("Legrand monthly probe: private API unavailable")
            return
        home_id = self.api.get_first_home_id()
        if home_id is None:
            _LOGGER.warning("Legrand monthly probe: no home found")
            return

        from .helpers.private_measure_decoder import decode_points_by_module
        from .models.fluid import FluidType

        modules = await self._module_service.async_get()
        electricity = [
            (module.id, module.bridge)
            for module in modules.values()
            if module.bridge is not None and module.fluid_type is FluidType.ELECTRICITY
        ]
        if not electricity:
            _LOGGER.warning("Legrand monthly probe: no electricity modules")
            return

        # Limit requests to one representative month per quarter and year.
        # Probe an alternate scale first, then a smaller 1day date window.
        for year in range(2022, 2026):
            for month, scale in (
                (1, "max"),
                (1, "1day"),
                (4, "1day"),
                (7, "1day"),
                (10, "1day"),
            ):
                start = int(datetime(year, month, 1, tzinfo=UTC).timestamp())
                stop = int(datetime(year, month + 1, 1, tzinfo=UTC).timestamp()) - 1
                try:
                    payload = await self.private_api.get_fluid_measures(
                        home_id=home_id,
                        modules=electricity,
                        fluid_type=FluidType.ELECTRICITY,
                        date_begin=start,
                        date_end=stop,
                        scale=scale,
                    )
                    decoded = decode_points_by_module(
                        payload, fluid_type=FluidType.ELECTRICITY
                    )
                    dates = [
                        point.timestamp
                        for series in decoded.values()
                        for point in series
                    ]
                    _LOGGER.warning(
                        "Legrand monthly probe %s-%02d scale=%s: points=%s "
                        "first=%s last=%s",
                        year,
                        month,
                        scale,
                        len(dates),
                        min(dates).isoformat() if dates else "none",
                        max(dates).isoformat() if dates else "none",
                    )
                except LegrandPrivateApiRateLimitError:
                    _LOGGER.warning("Legrand monthly probe: rate limited; stopping")
                    return
                except LegrandPrivateApiAuthenticationError:
                    _LOGGER.warning(
                        "Legrand monthly probe: authentication failed; stopping"
                    )
                    return
                except Exception as err:
                    _LOGGER.warning(
                        "Legrand monthly probe %s-%02d scale=%s: %s",
                        year,
                        month,
                        scale,
                        type(err).__name__,
                    )

    async def _async_update_data(self) -> LegrandEnergyData:
        """Fetch and assemble the latest Legrand Energy data."""
        try:
            modules = await self._module_service.async_get()

            contract: Contract | None = None
            tariff: TariffState | None = None
            measurements: LegrandMeasurements | None = None
            measurements_by_module: dict[str, LegrandMeasurements] = {}
            water_measurements_by_module: dict[str, FluidMeasurements] = {}
            gas_measurements_by_module: dict[str, FluidMeasurements] = {}
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
                    water_measurements_by_module,
                    gas_measurements_by_module,
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
                water_measurements_by_module=water_measurements_by_module,
                gas_measurements_by_module=gas_measurements_by_module,
                projections=projections,
            )

        except LegrandPrivateApiRateLimitError as err:
            if self.data is not None:
                _LOGGER.warning(
                    "Netatmo API rate limit reached, keeping previous values",
                )
                return self.data

            raise UpdateFailed("Netatmo API rate limit exceeded") from err

        except LegrandPrivateApiAuthenticationError as err:
            if self.data is not None:
                _LOGGER.warning(
                    "Private Netatmo authentication failed, "
                    "keeping previous values: %s",
                    err,
                )
                return self.data

            raise UpdateFailed(f"Private Netatmo authentication failed: {err}") from err

        except LegrandEnergyAuthenticationError as err:
            raise ConfigEntryAuthFailed("Netatmo OAuth authentication expired") from err

        except LegrandEnergyApiError as err:
            raise UpdateFailed(f"Unable to update Legrand Energy data: {err}") from err
