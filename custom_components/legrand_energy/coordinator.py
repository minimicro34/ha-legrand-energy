"""Data update coordinator for Legrand Energy."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import cast

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
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .contract_models import Contract
from .contract_parser import parse_contract
from .helpers.measurement_processor import MeasurementProcessor
from .helpers.private_measure_decoder import decode_energy_points_by_module
from .models import (
    LegrandEnergyData,
    LegrandMeasurements,
    LegrandModule,
    LegrandProjections,
)
from .private_api import (
    LegrandPrivateApi,
    LegrandPrivateApiAuthenticationError,
    LegrandPrivateApiError,
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
        self._contract: Contract | None = None
        self._contract_last_update: datetime | None = None

    async def _async_update_data(self) -> LegrandEnergyData:
        """Fetch and assemble the latest Legrand Energy data."""
        try:
            modules = await self.api.discover_modules()

            contract: Contract | None = None
            tariff: TariffState | None = None
            measurements: LegrandMeasurements | None = None
            measurements_by_module: dict[str, LegrandMeasurements] = {}
            projections: LegrandProjections | None = None

            home_id = self._get_home_id()

            if self.private_api is not None and home_id is not None:
                contract = await self._async_get_contract(home_id)

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
                ) = await self._async_get_all_measurements(
                    home_id=home_id,
                    modules=modules,
                    contract=contract,
                    tariff_engine=tariff_engine,
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
            _LOGGER.warning("Netatmo API rate limit reached, keeping previous values")

            if self.data is not None:
                return self.data

            raise UpdateFailed("Netatmo API rate limit exceeded") from err

        except LegrandPrivateApiAuthenticationError as err:
            raise ConfigEntryAuthFailed(
                "La session Web Netatmo a expiré. "
                "Mettez à jour les cookies privés dans les options."
            ) from err

        except LegrandEnergyApiError as err:
            raise UpdateFailed(f"Unable to update Legrand Energy data: {err}") from err

    async def _async_get_contract(
        self,
        home_id: str,
    ) -> Contract | None:
        """Return the cached contract and refresh it once per hour."""
        if self.private_api is None:
            return self._contract

        now = dt_util.now()

        cache_is_valid = (
            self._contract is not None
            and self._contract_last_update is not None
            and now - self._contract_last_update < timedelta(hours=1)
        )

        if cache_is_valid:
            return self._contract

        try:
            raw = await self.private_api.getcontracts(home_id)

        except LegrandPrivateApiAuthenticationError:
            raise

        except LegrandPrivateApiRateLimitError:
            raise

        except LegrandPrivateApiError as err:
            _LOGGER.warning(
                "Unable to update electricity contract, keeping cached data: %s",
                err,
            )
            return self._contract

        contract = parse_contract(raw)

        self._contract = contract
        self._contract_last_update = now

        return contract

    async def _async_get_all_measurements(
        self,
        home_id: str,
        modules: dict[str, LegrandModule],
        contract: Contract | None,
        tariff_engine: TariffEngine | None,
    ) -> tuple[
        LegrandMeasurements | None,
        dict[str, LegrandMeasurements],
        LegrandProjections | None,
    ]:
        """Fetch and calculate measurements for every electricity module."""
        if self.private_api is None:
            return None, {}, None

        circuits = [module for module in modules.values() if module.bridge is not None]

        if not circuits:
            return None, {}, None

        now = dt_util.now()

        today_start = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        week_start = today_start - timedelta(days=today_start.weekday())

        month_start = today_start.replace(day=1)

        year_start = today_start.replace(
            month=1,
            day=1,
        )

        try:
            raw = await self.private_api.get_electricity_measures(
                home_id=home_id,
                modules=[
                    (
                        module.id,
                        module.bridge,
                    )
                    for module in circuits
                    if module.bridge is not None
                ],
                date_begin=int(today_start.timestamp()),
                date_end=int(now.timestamp()),
            )

        except (
            LegrandPrivateApiAuthenticationError,
            LegrandPrivateApiRateLimitError,
        ):
            raise

        except LegrandPrivateApiError as err:
            _LOGGER.warning(
                "Unable to update private measurements, keeping cached data: %s",
                err,
            )

            previous_data = cast(
                LegrandEnergyData | None,
                getattr(self, "data", None),
            )

            if previous_data is not None:
                return (
                    previous_data.measurements,
                    previous_data.measurements_by_module,
                    previous_data.projections,
                )

            return None, {}, None

        points_by_module = decode_energy_points_by_module(raw)

        peak_price = (
            contract.peak_price
            if (contract is not None and contract.peak_price is not None)
            else 0.0
        )

        off_peak_price = (
            contract.off_peak_price
            if (contract is not None and contract.off_peak_price is not None)
            else 0.0
        )

        measurements_by_module: dict[
            str,
            LegrandMeasurements,
        ] = {}

        for module_id, points in points_by_module.items():
            MeasurementProcessor.apply_tariffs(
                points=points,
                tariff_engine=tariff_engine,
            )

            today_points = MeasurementProcessor.points_since(
                points,
                today_start,
            )

            week_points = MeasurementProcessor.points_since(
                points,
                week_start,
            )

            month_points = MeasurementProcessor.points_since(
                points,
                month_start,
            )

            year_points = MeasurementProcessor.points_since(
                points,
                year_start,
            )

            if not today_points:
                continue

            measurements_by_module[module_id] = MeasurementProcessor.build_measurements(
                today_points=today_points,
                week_points=week_points,
                month_points=month_points,
                year_points=year_points,
                peak_price=peak_price,
                off_peak_price=off_peak_price,
            )

        total_module = MeasurementProcessor.find_total_module(modules)

        measurements = (
            measurements_by_module.get(total_module.id)
            if total_module is not None
            else None
        )

        projections = (
            MeasurementProcessor.build_projections(
                measurements=measurements,
                now=now,
            )
            if measurements is not None
            else None
        )

        return (
            measurements,
            measurements_by_module,
            projections,
        )

    def _get_home_id(
        self,
    ) -> str | None:
        """Return the first home ID from cached topology data."""
        homesdata = self.api._homes_cache  # noqa: SLF001

        if homesdata is None:
            return None

        body = homesdata.get("body")

        if not isinstance(
            body,
            dict,
        ):
            return None

        homes = body.get("homes")

        if (
            not isinstance(
                homes,
                list,
            )
            or not homes
        ):
            return None

        home = homes[0]

        if not isinstance(
            home,
            dict,
        ):
            return None

        home_id = home.get("id")

        return (
            home_id
            if isinstance(
                home_id,
                str,
            )
            else None
        )
