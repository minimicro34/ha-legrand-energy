"""Parser for getcontracts."""

from __future__ import annotations

from .contract_models import (
    LegrandContract,
    LegrandContractTimetableEntry,
    LegrandContractZone,
)


def parse_contract(data: dict) -> LegrandContract | None:
    """Parse getcontracts."""
    contracts = data.get("body", {}).get("contracts", [])
    if not contracts:
        return None

    contract = contracts[0]

    zones = [
        LegrandContractZone(
            id=zone["id"],
            price=zone["price"],
            price_type=zone["price_type"],
        )
        for zone in contract.get("zones", [])
    ]

    timetable = [
        LegrandContractTimetableEntry(
            zone_id=item["zone_id"],
            m_offset=item["m_offset"],
        )
        for item in contract.get("timetable", [])
    ]

    peak = next((zone.price for zone in zones if zone.price_type == "peak"), None)
    off_peak = next((zone.price for zone in zones if zone.price_type == "off_peak"), None)

    return LegrandContract(
        id=contract["id"],
        type=contract["type"],
        tariff=contract["tariff"],
        tariff_option=contract["tariff_option"],
        power_threshold=contract["power_threshold"],
        power_unit=contract["contract_power_unit"],
        peak_price=peak,
        off_peak_price=off_peak,
        zones=zones,
        timetable=timetable,
    )