#!/usr/bin/env python3

import json

REQUEST_TYPES = """
sum_energy_self_consumption,
sum_energy_buy_from_grid,
sum_energy_buy_from_grid$0,
sum_energy_buy_from_grid$1,
sum_energy_buy_from_grid$2,
sum_energy_buy_from_grid$3,
sum_energy_buy_from_grid$4,
sum_energy_buy_from_grid$5,
sum_energy_buy_from_grid$6,
sum_energy_buy_from_grid$7,
sum_energy_buy_from_grid$8,
sum_energy_buy_from_grid$9,
sum_energy_buy_from_grid$10,
sum_energy_buy_from_grid$11,
sum_energy_buy_from_grid_price$0,
sum_energy_buy_from_grid_price$1,
sum_energy_buy_from_grid_price$2,
sum_energy_buy_from_grid_price$3,
sum_energy_buy_from_grid_price$4,
sum_energy_buy_from_grid_price$5,
sum_energy_buy_from_grid_price$6,
sum_energy_buy_from_grid_price$7,
sum_energy_buy_from_grid_price$8,
sum_energy_buy_from_grid_price$9,
sum_energy_buy_from_grid_price$10,
sum_energy_buy_from_grid_price$11,
sum_energy_resell_to_grid,
sum_energy_self_consumption,
sum_energy_resell_to_grid_price,
sum_energy_elec,
sum_energy_elec$2,
sum_energy_elec$0,
sum_energy_elec$1,
sum_energy_price$0,
sum_energy_price$1,
sum_energy_price$2
"""

TYPES = [t.strip() for t in REQUEST_TYPES.split(",") if t.strip()]

with open("response.json", encoding="utf-8") as f:
    data = json.load(f)

modules = data["body"]["home"]["modules"]

with open("decode_measurements.txt", "w", encoding="utf-8") as out:

    for module in modules:

        out.write("\n")
        out.write("=" * 80 + "\n")
        out.write(f"Module : {module['id']}\n")

        if "measures" not in module:
            out.write("Aucune mesure\n")
            continue

        for measure in module["measures"]:

            out.write(f"\nbeg_time : {measure.get('beg_time')}\n")
            out.write(f"step_time: {measure.get('step_time')}\n\n")

            values = measure["value"][-1]

            for i, value in enumerate(values):

                if i >= len(TYPES):
                    break

                out.write(
                    f"{i:02d}  {TYPES[i]:45} {value}\n"
                )

print("Résultat enregistré dans decode_measurements.txt")