"""Application credentials for Legrand Energy integration."""

from homeassistant.components.application_credentials import ApplicationCredentials
from .const import DOMAIN


class LegrandApplicationCredentials(ApplicationCredentials):
    """OAuth application credentials for Legrand Energy."""

    domain = DOMAIN
