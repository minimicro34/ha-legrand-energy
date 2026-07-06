import requests
import json
import time

ACCESS_TOKEN = "638b79cafe533bf059048bad|3b36bb07e94516e8ccc1f1f72075c51b"
HOME_ID = "69bd82c510bf0111d6055748"

url = "https://app.netatmo.net/syncapi/v1/homestatus"

params = {
    "home_id": HOME_ID,
    "device_types": '["NLE"]',
}

r = requests.get(
    url,
    headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
    params=params,
)

print(r.status_code)
print(json.dumps(r.json(), indent=2))