from datetime import UTC, datetime

from custom_components.legrand_energy.contract_models import (
    Contract,
    TariffPeriod,
    TariffZone,
)
from custom_components.legrand_energy.tariff_engine import TariffEngine


def test_price() -> None:
    contract = Contract(
        id="1",
        type="electricity",
        tariff="custom",
        tariff_option="peak_and_off_peak",
        power_threshold=6,
        power_unit="kVA",
        peak_price=0.20,
        off_peak_price=0.10,
        zones=[
            TariffZone(0, 0.20, "peak"),
            TariffZone(1, 0.10, "off_peak"),
        ],
        timetable=[
            TariffPeriod(0, 0),
            TariffPeriod(1, 1320),
        ],
    )

    engine = TariffEngine(contract)

    state = engine.state_at(
        datetime(2026, 7, 6, 23, 0, tzinfo=UTC)
    )

    assert state.price == 0.10
    assert state.zone_name == "off_peak"