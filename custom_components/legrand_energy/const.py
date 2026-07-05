"""Constants for the Legrand Energy integration."""

from __future__ import annotations

DOMAIN = "legrand_energy"
NAME = "Legrand Energy"

VERSION = "0.1.0"

MANUFACTURER = "Legrand"

# API Netatmo / Home + Control
API_BASE = "https://api.netatmo.com"
API_ENDPOINT = f"{API_BASE}/api"

AUTHORIZE_URL = "https://api.netatmo.com/oauth2/authorize"
TOKEN_URL = "https://api.netatmo.com/oauth2/token"

OAUTH_AUTHORIZE_URL = f"{API_BASE}/oauth2/authorize"
OAUTH_TOKEN_URL = f"{API_BASE}/oauth2/token"

# Home + Control endpoints
ENDPOINT_HOMESDATA = "/homesdata"
ENDPOINT_HOMETOPOLOGY = "/hometopology"
ENDPOINT_HOMESTATUS = "/homestatus"

# Energy scopes
SCOPES = [
    "topology.read",
    "meter.read",
    "network.read",
]

# Configuration keys
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_SUBSCRIPTION_KEY = "subscription_key"

# Default values
DEFAULT_TIMEOUT = 30

# Data refresh interval (seconds)
DEFAULT_SCAN_INTERVAL = 60
