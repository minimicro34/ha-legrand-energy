"""Parser for electricity contracts."""

from __future__ import annotations

from .contract_models import Contract, TariffPeriod, TariffZone


def parse_contract(data: dict) -> Contract | None:
    """Parse the first electricity contract."""
    contracts = data.get("body", {}).get("contracts", [])

    if not contracts:
        return None

    raw = contracts[0]

    peak_price = None
    off_peak_price = None

    zones: list[TariffZone] = []

    for zone in raw.get("zones", []):
        tariff_zone = TariffZone(
            id=zone["id"],
            price=zone["price"],
            price_type=zone["price_type"],
        )

        zones.append(tariff_zone)

        if tariff_zone.price_type == "peak":
            peak_price = tariff_zone.price

        elif tariff_zone.price_type == "off_peak":
            off_peak_price = tariff_zone.price

    timetable = [
        TariffPeriod(
            zone_id=item["zone_id"],
            minute_offset=item["m_offset"],
        )
        for item in raw.get("timetable", [])
    ]

    return Contract(
        id=raw["id"],
        type=raw["type"],
        tariff=raw["tariff"],
        tariff_option=raw["tariff_option"],
        power_threshold=raw["power_threshold"],
        power_unit=raw["contract_power_unit"],
        peak_price=peak_price,
        off_peak_price=off_peak_price,
        zones=zones,
        timetable=timetable,
    )