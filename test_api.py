import requests
import json
import time

ACCESS_TOKEN = "638b79cafe533bf059048bad|3b36bb07e94516e8ccc1f1f72075c51b"

headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

params = {
    "device_id": "00:04:74:12:24:d4",
    "module_id": "00:04:74:12:24:d4",
    "scale": "1day",
    "type": "sum_energy_buy_from_grid",
    "date_end": "last",
    "limit": 10,
}

r = requests.get(
    "https://api.netatmo.com/api/getmeasure",
    headers=headers,
    params=params,
)

print(r.status_code)
print(json.dumps(r.json(), indent=2))