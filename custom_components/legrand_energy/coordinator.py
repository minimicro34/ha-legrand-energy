"""DataUpdateCoordinator for Legrand Energy."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import LegrandEnergyApi, LegrandEnergyApiError

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

from .contract_models import Contract
from .contract_parser import parse_contract

from .models import LegrandModule

from .private_api import LegrandPrivateApi, LegrandPrivateApiError

from .helpers.energy_accumulator import EnergyAccumulator
from .helpers.module_statistics import ModuleStatistics
from .helpers.private_measure_decoder import decode_energy_points
from .helpers.statistics import total_cost, total_energy
from .helpers.daily_statistics import compute_daily_statistics
from .helpers.monthly_projection import project_month
from .helpers.projections import project_today

from .tariff_engine import TariffEngine

_LOGGER = logging.getLogger(__name__)

class LegrandEnergyCoordinator(DataUpdateCoordinator[dict[str, LegrandModule]]):
    """Legrand Energy coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        _LOGGER.error("Coordinator update started")
        self.entry = entry
        self.contract: Contract | None = None
        self.tariff_engine: TariffEngine | None = None

        async def update_tokens(access_token: str, refresh_token: str) -> None:
            """Persist refreshed OAuth tokens."""
            hass.config_entries.async_update_entry(
                entry,
                data={
                    **entry.data,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                },
            )

        session = async_get_clientsession(hass)

        self.api = LegrandEnergyApi(
            session=session,
            access_token=entry.data["access_token"],
            refresh_token=entry.data["refresh_token"],
            client_id=entry.data["client_id"],
            client_secret=entry.data["client_secret"],
            token_update_callback=update_tokens,
        )

        web_token = entry.options.get("web_token")
        self.private_api = (
            LegrandPrivateApi(session=session, web_token=web_token)
            if web_token
            else None
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, LegrandModule]:
        _LOGGER.error("_async_update_data CALLED")
        """Fetch data from APIs."""
        try:
            modules = await self.api.update()
            home_id = self._get_home_id()

            if self.private_api is not None and home_id is not None:
                await self._update_contract(home_id)
                await self._update_private_measures(modules, home_id)

            _LOGGER.error(
                "Coordinator state: modules=%d contract=%s tariff_engine=%s",
                len(modules),
                self.contract is not None,
                self.tariff_engine is not None,
            )
            return modules

        except LegrandEnergyApiError as err:
            raise UpdateFailed(f"Legrand Energy update failed: {err}") from err

    async def _update_private_measures(
    self,
    modules: dict[str, LegrandModule],
    home_id: str,
) -> None:
        """Update private electricity measures."""
        if self.private_api is None:
            return

        # Une seule référence temporelle pour tout le cycle de mise à jour.
        now_dt = dt_util.now()
        date_end = int(now_dt.timestamp())
        date_begin = date_end - (24 * 60 * 60)

        contract = self.contract
        engine = self.tariff_engine

        peak_price = (
            contract.peak_price
            if contract is not None and contract.peak_price is not None
            else 0.0
        )
        off_peak_price = (
            contract.off_peak_price
            if contract is not None and contract.off_peak_price is not None
            else 0.0
        )

        for module in modules.values():
            # Le bridge n'est pas un circuit de mesure.
            if module.bridge is None:
                continue

            try:
                suffix = int(module.id.rsplit("#", 1)[1])
            except (IndexError, ValueError):
                continue

            # Circuits électriques uniquement : #0 à #5.
            if suffix > 5:
                continue

            _LOGGER.debug(
                "Updating private measures for module %s",
                module.id,
            )

            try:
                result = await self.private_api.get_electricity_measure(
                    home_id=home_id,
                    module_id=module.id,
                    bridge=module.bridge,
                    date_begin=date_begin,
                    date_end=date_end,
                )
            except LegrandPrivateApiError as err:
                _LOGGER.warning(
                    "Private measure update failed for %s: %s",
                    module.id,
                    err,
                )
                continue

            # Certaines méthodes de l'API privée peuvent renvoyer
            # un tuple contenant le JSON et des métadonnées.
            raw = result[0] if isinstance(result, tuple) else result

            points = decode_energy_points(raw)

            # Le timetable du contrat est exprimé en heure locale.
            if engine is not None:
                for point in points:
                    local_timestamp = dt_util.as_local(point.timestamp)
                    state = engine.state_at(local_timestamp)

                    point.tariff = state.zone_name
                    point.zone_id = state.zone_id

            # Statistiques glissantes sur les dernières 24 heures.
            accumulator = EnergyAccumulator()

            for point in points:
                accumulator.add(point)

            # Statistiques de la journée civile locale, depuis minuit.
            today_points = [
                point
                for point in points
                if dt_util.as_local(point.timestamp).date() == now_dt.date()
            ]

            daily = compute_daily_statistics(
                today_points,
                peak_price=peak_price,
                off_peak_price=off_peak_price,
            )

            # Projection de la journée à partir du cumul depuis minuit.
            projection = project_today(
                energy=daily.total_energy,
                cost=daily.total_cost,
                now=now_dt,
            )

            # Projection mensuelle à partir d'une journée complète estimée.
            monthly = project_month(
                energy=projection.projected_energy,
                cost=projection.projected_cost,
                now=now_dt,
            )

            module.statistics = ModuleStatistics(
                points=points,
                total_energy=total_energy(points),
                total_cost=total_cost(points),
                dashboard_total=accumulator.total,
                daily=daily,
                projection=projection,
                monthly_projection=monthly,
            )

            if points:
                last_point = points[-1]

                module.energy_tariff1 = last_point.energy
                module.energy_tariff2 = None
                module.price_tariff1 = last_point.price
                module.price_tariff2 = None
                module.last_measure = int(
                    last_point.timestamp.timestamp()
                )

    async def _update_contract(self, home_id: str) -> None:
        """Update contract information."""
        if self.private_api is None:
            return

        try:
            _LOGGER.error("Updating contract for home_id %s", home_id)

            result = await self.private_api.getcontracts(home_id)

            if isinstance(result, tuple):
                raw = result[0]
            else:
                raw = result

        except LegrandPrivateApiError as err:
            _LOGGER.error("Private API failed: %s", err)
            return

        _LOGGER.error(
            "Raw contract type=%s value=%r",
            type(raw).__name__,
            raw,
        )

        self.contract = parse_contract(raw)
        _LOGGER.error("Parsed contract: %r", self.contract)

        if self.contract is not None:
            self.tariff_engine = TariffEngine(self.contract)
        else:
            self.tariff_engine = None

    def _get_home_id(self) -> str | None:
        """Return first home id from cached homesdata."""
        homesdata = self.api._homes_cache  # noqa: SLF001

        if not homesdata:
            return None

        homes = homesdata.get("body", {}).get("homes", [])
        if not homes:
            return None

        return homes[0].get("id")