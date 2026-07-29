"""Constants for Legrand Energy."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "legrand_energy"

MANUFACTURER = "Legrand"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)

OAUTH_AUTHORIZE_URL = "https://api.netatmo.com/oauth2/authorize"
OAUTH_TOKEN_URL = "https://api.netatmo.com/oauth2/token"

OAUTH_SCOPES: tuple[str, ...] = (
    "read_thermostat"
    "read_magellan",
    "write_magellan",
)
