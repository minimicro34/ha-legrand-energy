"""Legrand / Netatmo API client for Home + Control."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session

from .const import (
    API_ENDPOINT,
    DEFAULT_TIMEOUT,
    ENDPOINT_HOMESDATA,
    ENDPOINT_HOMESTATUS,
    ENDPOINT_HOMETOPOLOGY,
)

_LOGGER = logging.getLogger(__name__)
