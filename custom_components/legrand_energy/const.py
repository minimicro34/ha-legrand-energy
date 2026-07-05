"""Constants for the Legrand Energy integration."""

from __future__ import annotations

DOMAIN = "legrand_energy"

NAME = "Legrand Energy"

MANUFACTURER = "Legrand"

DEFAULT_SCAN_INTERVAL = 60
DEFAULT_TIMEOUT = 30

CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_SUBSCRIPTION_KEY = "subscription_key"

API_BASE_URL = "https://api.netatmo.com"

AUTHORIZE_URL = f"{API_BASE_URL}/oauth2/authorize"
TOKEN_URL = f"{API_BASE_URL}/oauth2/token"

HOME_API_BASE = "https://api.netatmo.com/api"

ENDPOINT_HOMESDATA = "/homesdata"
ENDPOINT_HOMESTATUS = "/homestatus"
ENDPOINT_HOMETOPOLOGY = "/hometopology"
ENDPOINT_ENERGY = "/energy"

SCOPES = [
    "topology.read",
    "meter.read",
    "network.read",
]
