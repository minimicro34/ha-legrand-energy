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
        """Log current and midnight-adjacent tariff state at INFO level."""
        now = dt_util.now()
        contract = self.data.contract if self.data is not None else None
        if contract is None:
            _LOGGER.info(
                "Legrand tariff fields diagnostic: time=%s contract=unavailable",
                now.isoformat(),
            )
            return

        engine = TariffEngine(contract)
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        samples = (
            ("previous_day_2359", midnight - timedelta(minutes=1)),
            ("today_0000", midnight),
            ("today_0005", midnight + timedelta(minutes=5)),
            ("now", now),
            ("next_day_0000", midnight + timedelta(days=1)),
        )
        _LOGGER.info(
            "Legrand tariff fields diagnostic: time=%s option=%s "
            "tariff=%s zones=%s timetable=%s",
            now.isoformat(),
            contract.tariff_option,
            contract.tariff,
            [(z.id, z.price_type, z.price) for z in contract.zones],
            [(p.zone_id, p.minute_offset) for p in contract.timetable],
        )
        for label, instant in samples:
            try:
                state = engine.state_at(instant)
                _LOGGER.info(
                    "Legrand tariff fields diagnostic: sample=%s time=%s "
                    "zone_id=%s zone=%s off_peak=%s price=%s next_change=%s",
                    label,
                    instant.isoformat(),
                    state.zone_id,
                    state.zone_name,
                    state.is_off_peak,
                    state.price,
                    state.next_change.isoformat() if state.next_change else None,
                )
            except ValueError as err:
                _LOGGER.info(
                    "Legrand tariff fields diagnostic: sample=%s time=%s error=%s",
                    label,
                    instant.isoformat(),
                    err,
                )

    async def async_debug_native_price_fields(self) -> None:
        """Inspect raw Netatmo price series without changing sensor values."""
        if self.private_api is None or self.data is None:
            _LOGGER.info("Legrand native price diagnostic: private API/data unavailable")
            return

        home_id = self.api.get_first_home_id()
        module = MeasurementProcessor.find_total_module(self.data.modules)
        if home_id is None or module is None:
            _LOGGER.info("Legrand native price diagnostic: home/total module unavailable")
            return

        now = dt_util.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        fields = (
            "sum_energy_elec,sum_energy_elec$0,sum_energy_elec$1,"
            "sum_energy_elec$2,sum_energy_price$0,sum_energy_price$1,"
            "sum_energy_price$2"
        )
        home = {
            "id": home_id,
            "modules": [{"id": module.id, "type": fields}],
            "rooms": [],
        }
        if module.bridge is not None:
            home["modules"][0]["bridge"] = module.bridge

        try:
            payload = await self.private_api.get_home_measure(
                home=home,
                scale="5min",
                real_time=True,
                date_begin=int((midnight - timedelta(days=1)).timestamp()),
                date_end=int(now.timestamp()),
            )
        except Exception as err:
            _LOGGER.warning(
                "Legrand native price diagnostic: gethomemeasure failed (%s)",
                type(err).__name__,
            )
            return

        body = payload.get("body")
        home_data = body.get("home") if isinstance(body, dict) else None
        modules = home_data.get("modules") if isinstance(home_data, dict) else None
        _LOGGER.info(
            "Legrand native price diagnostic: requested_fields=%s response_modules=%s",
            fields,
            len(modules) if isinstance(modules, list) else "missing",
        )
        if not isinstance(modules, list):
            return

        field_names = fields.split(",")
        for item in modules:
            if not isinstance(item, dict) or item.get("id") != module.id:
                continue
            measures = item.get("measures")
            if not isinstance(measures, list):
                _LOGGER.info("Legrand native price diagnostic: measures=missing")
                continue
            for measure in measures:
                if not isinstance(measure, dict):
                    continue
                start = measure.get("beg_time")
                step = measure.get("step_time")
                rows = measure.get("value")
                if not isinstance(start, int) or not isinstance(step, int) or not isinstance(rows, list):
                    _LOGGER.info("Legrand native price diagnostic: invalid measure structure")
                    continue
                _LOGGER.info(
                    "Legrand native price diagnostic: beg_time=%s step_time=%s rows=%d",
                    start, step, len(rows),
                )
                by_day = {}
                for index, row in enumerate(rows):
                    if not isinstance(row, list):
                        continue
                    stamp = datetime.fromtimestamp(start + index * step, dt_util.UTC)
                    local = dt_util.as_local(stamp)
                    day = local.date().isoformat()
                    prices = {
                        field_names[pos]: row[pos] if pos < len(row) else None
                        for pos in (4, 5, 6)
                    }
                    energies = {
                        field_names[pos]: row[pos] if pos < len(row) else None
                        for pos in (1, 2, 3)
                    }
                    if any(value is not None for value in prices.values()):
                        by_day.setdefault(day, []).append((local.isoformat(), prices, energies))
                for day, samples in sorted(by_day.items()):
                    _LOGGER.info(
                        "Legrand native price diagnostic: day=%s nonempty_rows=%d first=%s last=%s",
                        day, len(samples), samples[0], samples[-1],
                    )
                if not by_day:
                    _LOGGER.info(
                        "Legrand native price diagnostic: no non-null price values in %d rows",
                        len(rows),
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
