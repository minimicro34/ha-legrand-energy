"""Tests for Legrand Energy authentication persistence."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.legrand_energy.authentication_store import (
    PRIVATE_COOKIE_NAMES,
    ConfigEntryAuthenticationStore,
)
from custom_components.legrand_energy.models.auth import PrivateSession


@pytest.mark.asyncio
async def test_save_private_updates_config_entry() -> None:
    hass = MagicMock()
    entry = MagicMock()
    entry.data = {"existing": "value", "refresh_token_web": "old-refresh"}

    cookies = {
        PRIVATE_COOKIE_NAMES["refresh_token_web"]: "new-refresh",
        PRIVATE_COOKIE_NAMES["laravel_session"]: "laravel",
        PRIVATE_COOKIE_NAMES["xsrf_token"]: "xsrf",
    }
    session = PrivateSession(web_token="web-token", cookies=cookies)

    store = ConfigEntryAuthenticationStore(hass, entry)
    await store.async_save_private(session)

    hass.config_entries.async_update_entry.assert_called_once_with(
        entry,
        data={
            "existing": "value",
            "refresh_token_web": "new-refresh",
            "web_token": "web-token",
            "laravel_session": "laravel",
            "xsrf_token": "xsrf",
        },
    )
