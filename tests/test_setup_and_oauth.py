"""Tests for integration setup, OAuth helpers, and diagnostics."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant import config_entries
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.legrand_energy import async_setup_entry, async_unload_entry
from custom_components.legrand_energy.application_credentials import (
    async_get_authorization_server,
    async_get_description_placeholders,
)
from custom_components.legrand_energy.const import (
    DOMAIN,
    OAUTH_AUTHORIZE_URL,
    OAUTH_TOKEN_URL,
)
from custom_components.legrand_energy.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.legrand_energy.models.auth import PrivateSession
from custom_components.legrand_energy.oauth2 import (
    async_get_access_token,
    async_get_implementation,
    async_get_session,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


def _entry(data=None, options=None) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Legrand EcoMeter",
        data=data or {},
        options=options or {},
        source=config_entries.SOURCE_USER,
        unique_id=DOMAIN,
    )


@pytest.mark.asyncio
async def test_setup_with_existing_private_session(hass) -> None:
    entry = _entry(
        {
            "web_token": "web-token",
            "refresh_token_web": "refresh",
            "laravel_session": "laravel",
        }
    )
    entry.add_to_hass(hass)
    oauth_session = MagicMock()
    oauth_session.async_ensure_token_valid = AsyncMock()
    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()

    with (
        patch(
            "custom_components.legrand_energy.async_get_session",
            new=AsyncMock(return_value=oauth_session),
        ),
        patch(
            "custom_components.legrand_energy.LegrandEnergyCoordinator",
            return_value=coordinator,
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new=AsyncMock(),
        ) as forward,
    ):
        assert await async_setup_entry(hass, entry) is True

    coordinator.async_config_entry_first_refresh.assert_awaited_once()
    assert entry.runtime_data is coordinator
    forward.assert_awaited_once()


@pytest.mark.asyncio
async def test_setup_logs_in_with_legacy_credentials(hass) -> None:
    entry = _entry({"username": "user@example.com", "password": "secret"})
    entry.add_to_hass(hass)
    oauth_session = MagicMock()
    oauth_session.async_ensure_token_valid = AsyncMock()
    private_session = PrivateSession(web_token="web-token", cookies={})
    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()

    with (
        patch(
            "custom_components.legrand_energy.async_get_session",
            new=AsyncMock(return_value=oauth_session),
        ),
        patch(
            "custom_components.legrand_energy.AuthenticationManager.login_private",
            new=AsyncMock(return_value=private_session),
        ) as login,
        patch(
            "custom_components.legrand_energy.LegrandEnergyCoordinator",
            return_value=coordinator,
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new=AsyncMock(),
        ),
    ):
        assert await async_setup_entry(hass, entry) is True

    login.assert_awaited_once_with(username="user@example.com", password="secret")


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 499])
async def test_setup_rejects_invalid_oauth_token(hass, status) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    oauth_session = MagicMock()
    oauth_session.async_ensure_token_valid = AsyncMock(
        side_effect=aiohttp.ClientResponseError(
            MagicMock(real_url="https://example.invalid"),
            (),
            status=status,
        )
    )

    with (
        patch(
            "custom_components.legrand_energy.async_get_session",
            new=AsyncMock(return_value=oauth_session),
        ),
        pytest.raises(ConfigEntryAuthFailed),
    ):
        await async_setup_entry(hass, entry)


@pytest.mark.asyncio
async def test_setup_retries_server_oauth_error(hass) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    oauth_session = MagicMock()
    oauth_session.async_ensure_token_valid = AsyncMock(
        side_effect=aiohttp.ClientResponseError(
            MagicMock(real_url="https://example.invalid"),
            (),
            status=503,
        )
    )

    with (
        patch(
            "custom_components.legrand_energy.async_get_session",
            new=AsyncMock(return_value=oauth_session),
        ),
        pytest.raises(ConfigEntryNotReady, match="validate OAuth2 token"),
    ):
        await async_setup_entry(hass, entry)


@pytest.mark.asyncio
async def test_setup_retries_network_oauth_error(hass) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    oauth_session = MagicMock()
    oauth_session.async_ensure_token_valid = AsyncMock(
        side_effect=aiohttp.ClientConnectionError("offline")
    )

    with (
        patch(
            "custom_components.legrand_energy.async_get_session",
            new=AsyncMock(return_value=oauth_session),
        ),
        pytest.raises(ConfigEntryNotReady, match="validate OAuth2 token"),
    ):
        await async_setup_entry(hass, entry)


@pytest.mark.asyncio
async def test_unload_entry(hass) -> None:
    entry = _entry()
    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new=AsyncMock(return_value=True),
    ) as unload:
        assert await async_unload_entry(hass, entry) is True
    unload.assert_awaited_once()


@pytest.mark.asyncio
async def test_application_credentials_helpers(hass) -> None:
    server = await async_get_authorization_server(hass)
    assert server.authorize_url == OAUTH_AUTHORIZE_URL
    assert server.token_url == OAUTH_TOKEN_URL
    assert await async_get_description_placeholders(hass) == {
        "console_url": "https://dev.netatmo.com/apps/"
    }


@pytest.mark.asyncio
async def test_oauth_helpers(hass) -> None:
    entry = _entry()
    implementation = MagicMock()

    with patch(
        "custom_components.legrand_energy.oauth2.config_entry_oauth2_flow.async_get_config_entry_implementation",
        new=AsyncMock(return_value=implementation),
    ):
        assert await async_get_implementation(hass, entry) is implementation

    session = MagicMock()
    session.async_ensure_token_valid = AsyncMock()
    session.token = {"access_token": "access-token"}

    with patch(
        "custom_components.legrand_energy.oauth2.async_get_session",
        new=AsyncMock(return_value=session),
    ):
        assert await async_get_access_token(hass, entry) == "access-token"

    session.token = {}
    with (
        patch(
            "custom_components.legrand_energy.oauth2.async_get_session",
            new=AsyncMock(return_value=session),
        ),
        pytest.raises(ValueError, match="access token missing"),
    ):
        await async_get_access_token(hass, entry)


@pytest.mark.asyncio
async def test_oauth_session_construction(hass) -> None:
    entry = _entry()
    implementation = MagicMock()
    constructed = MagicMock()

    with (
        patch(
            "custom_components.legrand_energy.oauth2.async_get_implementation",
            new=AsyncMock(return_value=implementation),
        ),
        patch(
            "custom_components.legrand_energy.oauth2.OAuth2Session",
            return_value=constructed,
        ) as session_cls,
    ):
        assert await async_get_session(hass, entry) is constructed

    session_cls.assert_called_once_with(hass, entry, implementation)


@pytest.mark.asyncio
async def test_diagnostics_redacts_credentials(hass) -> None:
    entry = _entry(
        {
            "username": "user@example.com",
            "password": "secret",
            "web_token": "private",
            "safe": "visible",
        }
    )
    coordinator = MagicMock()
    coordinator.api.homesdata = AsyncMock(
        return_value={"access_token": "secret-token", "home": "visible"}
    )
    entry.runtime_data = coordinator

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"]["safe"] == "visible"
    assert diagnostics["entry"]["password"] == "**REDACTED**"
    assert diagnostics["homesdata"]["home"] == "visible"
    assert diagnostics["homesdata"]["access_token"] == "**REDACTED**"
