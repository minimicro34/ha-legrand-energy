"""Constants for the Legrand Energy integration."""

from __future__ import annotations

DOMAIN = "legrand_energy"

MANUFACTURER = "Legrand"

API_HOST = "https://api.netatmo.com"

AUTHORIZE_URL = f"{API_HOST}/oauth2/authorize"
TOKEN_URL = f"{API_HOST}/oauth2/token"

API_BASE = f"{API_HOST}/api"

SCOPES: list[str] = [
    "topology.read",
    "meter.read",
    "network.read",
]

DEFAULT_TIMEOUT = 30

USER_AGENT = "ha-legrand-energy/0.0.1"

CONF_SUBSCRIPTION_KEY = "subscription_key"
