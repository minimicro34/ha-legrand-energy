"""The Legrand Energy integration."""

from __future__ import annotations

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LegrandEnergyApi
from .authentication import AuthenticationManager
from .authentication_store import (
    PRIVATE_COOKIE_NAMES,
    ConfigEntryAuthenticationStore,
)
from .const import DOMAIN
from .coordinator import LegrandEnergyCoordinator
from .models.auth import PrivateSession
from .oauth2 import async_get_session
from .private_api import LegrandPrivateApi
from .services.private import PrivateAuthService

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Legrand Energy from a config entry."""
    session = async_get_clientsession(hass)

    def private_value(key: str) -> str | None:
        """Return a private authentication value."""
        data_value = entry.data.get(key)

        if isinstance(data_value, str) and data_value:
            return data_value

        option_value = entry.options.get(key)

        if isinstance(option_value, str) and option_value:
            return option_value

        return None

    try:
        oauth_session = await async_get_session(
            hass,
            entry,
        )
    except config_entry_oauth2_flow.ImplementationUnavailableError as err:
        raise ConfigEntryNotReady(
            "OAuth2 implementation temporarily unavailable"
        ) from err

    try:
        await oauth_session.async_ensure_token_valid()
    except aiohttp.ClientResponseError as err:
        if 400 <= err.status < 500:
            raise ConfigEntryAuthFailed from err

        raise ConfigEntryNotReady(
            "Unable to validate OAuth2 token, will retry"
        ) from err
    except aiohttp.ClientError as err:
        raise ConfigEntryNotReady(
            "Unable to validate OAuth2 token, will retry"
        ) from err

    private_service = PrivateAuthService(
        session=session,
    )

    web_token = private_value("web_token")
    private_session: PrivateSession | None = None

    if web_token is not None:
        private_cookies: dict[str, str] = {}

        for config_key, cookie_name in PRIVATE_COOKIE_NAMES.items():
            value = private_value(config_key)

            if value is not None:
                private_cookies[cookie_name] = value

        private_session = PrivateSession(
            web_token=web_token,
            cookies=private_cookies,
        )

    authentication_store = ConfigEntryAuthenticationStore(
        hass=hass,
        entry=entry,
    )

    authentication = AuthenticationManager(
        oauth_session=oauth_session,
        private_service=private_service,
        private_session=private_session,
        store=authentication_store,
    )

    if private_session is None:
        username = entry.data.get("username")
        password = entry.data.get("password")

        if (
            isinstance(username, str)
            and username
            and isinstance(password, str)
            and password
        ):
            private_session = await authentication.login_private(
                username=username,
                password=password,
            )

    api = LegrandEnergyApi(
        session=session,
        authentication=authentication,
    )

    private_api = (
        LegrandPrivateApi(
            session=session,
            authentication=authentication,
        )
        if private_session is not None
        else None
    )

    coordinator = LegrandEnergyCoordinator(
        hass=hass,
        config_entry=entry,
        api=api,
        private_api=private_api,
    )

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    async def debug_homestatus(_call: ServiceCall) -> None:
        """Run a sanitized private Home + Control status probe."""
        await coordinator.async_debug_homestatus()

    hass.services.async_register(
        DOMAIN,
        "debug_homestatus",
        debug_homestatus,
    )

    async def debug_measure_types(_call: ServiceCall) -> None:
        """Probe candidate private Home + Control measurement types."""
        await coordinator.async_debug_measure_types()

    hass.services.async_register(
        DOMAIN,
        "debug_measure_types",
        debug_measure_types,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload a Legrand Energy config entry."""
    return await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )
