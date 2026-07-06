"""Constants for Legrand Energy."""

from datetime import timedelta

DOMAIN = "legrand_energy"

API_BASE = "https://api.netatmo.com/api"
APP_API_BASE = "https://app.netatmo.net/api"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)

MANUFACTURER = "Legrand"
PLATFORMS = ["sensor"]
