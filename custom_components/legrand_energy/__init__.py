"""The Legrand Energy integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LegrandEnergyApi
from .authentication import AuthenticationManager
from .authentication_store import (
    PRIVATE_COOKIE_NAMES,
    ConfigEntryAuthenticationStore,
)
from .coordinator import LegrandEnergyCoordinator
from .models.auth import AuthenticationState, PrivateSession
from .oauth2 import async_get_session
from .private_api import LegrandPrivateApi
from .services.private import PrivateAuthService

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]

PRIVATE_AUTH_KEYS = (
    "web_token",
    *PRIVATE_COOKIE_NAMES,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Legrand Energy from a config entry."""
    session = async_get_clientsession(hass)

    def private_value(key: str) -> str | None:
        """Return a private authentication value."""
        option_value = entry.options.get(key)

        if isinstance(option_value, str) and option_value:
            return option_value

        data_value = entry.data.get(key)

        if isinstance(data_value, str) and data_value:
            return data_value

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

    # Refresh the token immediately when it is already expired.
    await oauth_session.async_ensure_token_valid()

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

    authentication_state = AuthenticationState(
        private=private_session,
    )

    authentication_store = ConfigEntryAuthenticationStore(
        hass=hass,
        entry=entry,
    )

    authentication = AuthenticationManager(
        oauth_session=oauth_session,
        private_service=private_service,
        state=authentication_state,
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

    async def async_entry_updated(
        hass: HomeAssistant,
        updated_entry: ConfigEntry,
    ) -> None:
        """Apply user-updated options and reload the integration."""
        new_data: dict[str, Any] = dict(updated_entry.data)

        for key in PRIVATE_AUTH_KEYS:
            option_value = updated_entry.options.get(key)

            if isinstance(option_value, str):
                if option_value:
                    new_data[key] = option_value
                else:
                    new_data.pop(key, None)

        if new_data != updated_entry.data:
            hass.config_entries.async_update_entry(
                updated_entry,
                data=new_data,
            )

        await hass.config_entries.async_reload(updated_entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(async_entry_updated))

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
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
