"""OAuth application credentials."""

from homeassistant.components.application_credentials import (
    ApplicationCredentials,
)

from .const import DOMAIN


class LegrandApplicationCredentials(ApplicationCredentials):
    """Legrand OAuth credentials."""

    domain = DOMAIN
