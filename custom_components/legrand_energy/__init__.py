"""The Legrand Energy integration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LegrandEnergyApi
from .authentication import AuthenticationManager
from .authentication_store import (
    PRIVATE_COOKIE_NAMES,
    ConfigEntryAuthenticationStore,
)
from .coordinator import LegrandEnergyCoordinator
from .models.auth import AuthenticationState, OAuthSession, PrivateSession
from .private_api import LegrandPrivateApi
from .services.oauth import OAuthService
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

    obtained_at_value = entry.data.get("obtained_at")
    obtained_at = datetime.now(UTC)

    if isinstance(obtained_at_value, str):
        obtained_at = datetime.fromisoformat(obtained_at_value)

    expires_in_value = entry.data.get("expires_in", 0)
    expires_in = expires_in_value if isinstance(expires_in_value, int) else 0

    token_type_value = entry.data.get("token_type", "Bearer")
    token_type = token_type_value if isinstance(token_type_value, str) else "Bearer"

    oauth_service = OAuthService(
        session=session,
        client_id=entry.data["client_id"],
        client_secret=entry.data["client_secret"],
    )

    private_service = PrivateAuthService(
        session=session,
    )

    oauth_session = OAuthSession(
        access_token=entry.data["access_token"],
        refresh_token=entry.data["refresh_token"],
        expires_in=expires_in,
        obtained_at=obtained_at,
        token_type=token_type,
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
        oauth=oauth_session,
        private=private_session,
    )

    authentication_store = ConfigEntryAuthenticationStore(
        hass=hass,
        entry=entry,
    )

    authentication = AuthenticationManager(
        oauth_service=oauth_service,
        private_service=private_service,
        state=authentication_state,
        store=authentication_store,
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
