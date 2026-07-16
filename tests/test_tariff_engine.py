"""Tests for the tariff engine."""

from datetime import UTC, datetime

from custom_components.legrand_energy.contract_models import (
    Contract,
    TariffPeriod,
    TariffZone,
)
from custom_components.legrand_energy.tariff_engine import TariffEngine


def make_contract() -> Contract:
    """Return a test contract."""
    return Contract(
        id="contract-1",
        type="electricity",
        tariff="custom",
        tariff_option="peak_and_off_peak",
        power_threshold=6,
        power_unit="kVA",
        peak_price=0.2159,
        off_peak_price=0.1438,
        zones=[
            TariffZone(
                id=0,
                price=0.2159,
                price_type="peak",
            ),
            TariffZone(
                id=1,
                price=0.1438,
                price_type="off_peak",
            ),
        ],
        timetable=[
            TariffPeriod(
                zone_id=0,
                minute_offset=0,
            ),
            TariffPeriod(
                zone_id=1,
                minute_offset=5,
            ),
            TariffPeriod(
                zone_id=0,
                minute_offset=335,
            ),
        ],
    )


def test_peak_state() -> None:
    """Test peak state."""
    engine = TariffEngine(make_contract())

    when = datetime(
        2026,
        7,
        6,
        6,
        0,
        tzinfo=UTC,
    )

    state = engine.state_at(when)

    assert state.zone_id == 0
    assert state.zone_name == "peak"
    assert state.price == 0.2159


def test_off_peak_state() -> None:
    """Test off-peak state."""
    engine = TariffEngine(make_contract())

    when = datetime(
        2026,
        7,
        6,
        0,
        10,
        tzinfo=UTC,
    )

    state = engine.state_at(when)

    assert state.zone_id == 1
    assert state.zone_name == "off_peak"
    assert state.price == 0.1438


def test_next_change_is_timezone_aware() -> None:
    """Test next tariff change has timezone information."""
    engine = TariffEngine(make_contract())

    when = datetime(
        2026,
        7,
        6,
        0,
        1,
        tzinfo=UTC,
    )

    next_change = engine.next_change(when)

    assert next_change.tzinfo is not None
    assert next_change.second == 0
    assert next_change.microsecond == 0


def test_is_off_peak() -> None:
    """Test off-peak helper."""
    engine = TariffEngine(make_contract())

    when = datetime(
        2026,
        7,
        6,
        0,
        10,
        tzinfo=UTC,
    )

    assert engine.is_off_peak(when) is True
    assert engine.is_peak(when) is False
