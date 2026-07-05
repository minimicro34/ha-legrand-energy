"""Constants for Legrand Home + Control."""

DOMAIN = "legrand_energy"

API_BASE = "https://api.netatmo.com"

AUTHORIZE_URL = f"{API_BASE}/oauth2/authorize"
TOKEN_URL = f"{API_BASE}/oauth2/token"

API_URL = "https://api.netatmo.com/api"

DEFAULT_TIMEOUT = 30

SCOPES = [
    "topology.read",
    "meter.read",
    "network.read",
]
