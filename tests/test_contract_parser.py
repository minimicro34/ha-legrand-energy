"""Tests for contract parser."""

from custom_components.legrand_energy.contract_parser import parse_contract


def test_parse_contract() -> None:
    data = {
        "body": {
            "contracts": [
                {
                    "id": "contract1",
                    "type": "electricity",
                    "tariff": "custom",
                    "tariff_option": "peak_and_off_peak",
                    "contract_power_unit": "kVA",
                    "power_threshold": 6,
                    "zones": [
                        {"id": 0, "price": 0.2159, "price_type": "peak"},
                        {"id": 1, "price": 0.1438, "price_type": "off_peak"},
                    ],
                    "timetable": [
                        {"zone_id": 0, "m_offset": 0},
                        {"zone_id": 1, "m_offset": 1320},
                    ],
                }
            ]
        }
    }

    contract = parse_contract(data)

    assert contract is not None
    assert contract.type == "electricity"
    assert contract.tariff == "custom"
    assert contract.tariff_option == "peak_and_off_peak"
    assert contract.power_threshold == 6
    assert contract.power_unit == "kVA"
    assert contract.peak_price == 0.2159
    assert contract.off_peak_price == 0.1438