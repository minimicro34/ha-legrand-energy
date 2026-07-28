"""OAuth2 helpers for Legrand Energy."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.config_entry_oauth2_flow import (
    AbstractOAuth2Implementation,
    OAuth2Session,
)


async def async_get_implementation(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> AbstractOAuth2Implementation:
    """Return the OAuth implementation for this config entry."""
    return await config_entry_oauth2_flow.async_get_config_entry_implementation(
        hass,
        entry,
    )


async def async_get_session(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> OAuth2Session:
    """Return an OAuth2 session for this config entry."""
    implementation = await async_get_implementation(
        hass,
        entry,
    )

    return OAuth2Session(
        hass,
        entry,
        implementation,
    )


async def async_get_access_token(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> str:
    """Return a valid OAuth access token."""
    session = await async_get_session(
        hass,
        entry,
    )

    await session.async_ensure_token_valid()

    token = session.token.get("access_token")

    if not isinstance(token, str):
        raise ValueError("OAuth access token missing")

    return token
