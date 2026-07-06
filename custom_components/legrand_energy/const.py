"""Constants for the Legrand Energy integration."""

from datetime import timedelta

DOMAIN = "legrand_energy"

API_BASE = "https://api.netatmo.com/api"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)

MANUFACTURER = "Legrand"
ATTRIBUTION = "Data provided by Legrand Home + Control"

PLATFORMS = ["sensor"]
