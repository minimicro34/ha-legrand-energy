"""Data update coordinator for Legrand Energy."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

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
from .helpers.measurement_processor import MeasurementProcessor
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

    def cached_energy_history(
        self, *, start: datetime, end: datetime
    ) -> list[dict[str, object]]:
        """Return the total electricity series from the private API cache."""
        if self._measurement_service is None or self.data is None:
            return []
        total_module = MeasurementProcessor.find_total_module(self.data.modules)
        if total_module is None:
            return []
        return self._measurement_service.cached_energy_history(
            total_module.id, start=start, end=end
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

    async def async_debug_tariff_fields(self) -> None:
        """Probe raw electricity columns for one completed local day."""
        if self.private_api is None or self.data is None:
            _LOGGER.warning("Legrand Energy tariff probe: private API unavailable")
            return

        home_id = self.api.get_first_home_id()
        module = MeasurementProcessor.find_total_module(self.data.modules)
        if home_id is None or module is None or module.bridge is None:
            _LOGGER.warning("Legrand Energy tariff probe: total module unavailable")
            return

        day_start = (dt_util.now() - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)
        fields = ("total", "$0", "$1", "$2")
        for scale in ("1day", "5min"):
            payload = await self.private_api.get_electricity_measures(
                home_id=home_id,
                modules=[(module.id, module.bridge)],
                date_begin=int(day_start.timestamp()),
                date_end=int(day_end.timestamp()) - 1,
                scale=scale,
            )
            body = payload.get("body")
            home = body.get("home") if isinstance(body, dict) else None
            modules = home.get("modules") if isinstance(home, dict) else None
            measures = (
                modules[0].get("measures")
                if isinstance(modules, list)
                and modules
                and isinstance(modules[0], dict)
                else None
            )
            sums = [0.0] * 4
            counts = [0] * 4
            steps: set[int] = set()
            rows = 0
            if isinstance(measures, list):
                for measure in measures:
                    if not isinstance(measure, dict):
                        continue
                    step = measure.get("step_time")
                    if isinstance(step, int):
                        steps.add(step)
                    values = measure.get("value")
                    if not isinstance(values, list):
                        continue
                    for row in values:
                        if not isinstance(row, list):
                            continue
                        rows += 1
                        for index in range(4):
                            if (
                                index < len(row)
                                and isinstance(row[index], (int, float))
                                and not isinstance(row[index], bool)
                            ):
                                sums[index] += float(row[index])
                                counts[index] += 1
            summary = {
                name: {"sum_wh": round(sums[i], 3), "count": counts[i]}
                for i, name in enumerate(fields)
            }
            _LOGGER.warning(
                "Legrand Energy tariff probe: day=%s scale=%s rows=%s "
                "steps_seconds=%s energy_columns=%s",
                day_start.date(),
                scale,
                rows,
                sorted(steps),
                summary,
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
