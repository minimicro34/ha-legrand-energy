"""Parser for Legrand gethomemeasure."""

from __future__ import annotations

from .models import MeasurePoint, ModuleMeasurement


def parse_gethomemeasure(
    homesdata: dict,
    gethomemeasure: dict,
    request_types: list[str] | tuple[str, ...],
) -> dict[str, ModuleMeasurement]:
    """Parse gethomemeasure response."""

    modules: dict[str, ModuleMeasurement] = {}

    #
    # Build module index from homesdata
    #
    module_info: dict[str, dict] = {}

    for home in homesdata["body"]["homes"]:
        for module in home["modules"]:

            module_info[module["id"]] = {
                "name": module.get("name", module["id"]),
                "type": module.get("type", ""),
                "bridge": module.get("bridge"),
            }

    #
    # Parse measurements
    #
    for module in gethomemeasure["body"]["home"]["modules"]:

        module_id = module["id"]

        info = module_info.get(
            module_id,
            {
                "name": module_id,
                "type": "",
                "bridge": None,
            },
        )

        measurement = ModuleMeasurement(
            id=module_id,
            name=info["name"],
            type=info["type"],
            bridge=info["bridge"],
        )

        for block in module.get("measures", []):

            start = block["beg_time"]
            step = block["step_time"]

            for index, row in enumerate(block["value"]):

                timestamp = start + index * step

                values = {
                    name: value
                    for name, value in zip(request_types, row)
                    if value is not None
                }

                measurement.history.append(
                    MeasurePoint(
                        timestamp=timestamp,
                        values=values,
                    )
                )

        measurement.raw = module

        modules[module_id] = measurement

    return modules