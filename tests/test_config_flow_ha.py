"""Home Assistant integration tests for the Legrand Energy config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.legrand_energy.config_flow import LegrandEnergyConfigFlow
from custom_components.legrand_energy.const import DOMAIN
from custom_components.legrand_energy.services.private import PrivateSession

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


@pytest.mark.asyncio
async def test_reconfigure_private_credentials(
    hass: HomeAssistant,
) -> None:
    """Test reconfiguring private Home + Control credentials."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Legrand EcoMeter",
        data={
            "auth_implementation": "netatmo",
            "token": {
                "access_token": "oauth-access-token",
                "refresh_token": "oauth-refresh-token",
            },
            "username": "old@example.com",
            "password": "old-password",
            "web_token": "old-web-token",
            "refresh_token_web": "old-refresh",
            "laravel_session": "old-session",
        },
        source=config_entries.SOURCE_USER,
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)

    private_session = PrivateSession(
        web_token="new-web-token",
        cookies={
            "authnetatmocomrefresh_token": "new-refresh",
            "authnetatmocomlaravel_session": "new-session",
        },
    )

    with patch(
        "custom_components.legrand_energy.config_flow.PrivateAuthService.login",
        new=AsyncMock(return_value=private_session),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reconfigure"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "new@example.com",
                "password": "new-password",
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    assert entry.data["username"] == "new@example.com"
    assert entry.data["password"] == "new-password"
    assert entry.data["web_token"] == "new-web-token"
    assert entry.data["refresh_token_web"] == "new-refresh"
    assert entry.data["laravel_session"] == "new-session"

    assert entry.data["auth_implementation"] == "netatmo"
    assert entry.data["token"]["access_token"] == "oauth-access-token"


@pytest.mark.asyncio
async def test_reconfigure_replaces_old_private_session(
    hass: HomeAssistant,
) -> None:
    """Test that stale private authentication data is removed."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Legrand EcoMeter",
        data={
            "auth_implementation": "netatmo",
            "token": {
                "access_token": "oauth-access-token",
            },
            "username": "old@example.com",
            "password": "old-password",
            "web_token": "old-web-token",
            "refresh_token_web": "stale-refresh",
            "laravel_session": "stale-session",
        },
        source=config_entries.SOURCE_USER,
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)

    private_session = PrivateSession(
        web_token="new-web-token",
        cookies={},
    )

    with patch(
        "custom_components.legrand_energy.config_flow.PrivateAuthService.login",
        new=AsyncMock(return_value=private_session),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "new@example.com",
                "password": "new-password",
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    assert entry.data["web_token"] == "new-web-token"
    assert "refresh_token_web" not in entry.data
    assert "laravel_session" not in entry.data


@pytest.mark.asyncio
async def test_oauth_reauth_confirmation(
    hass: HomeAssistant,
) -> None:
    """Test that OAuth reauthentication starts with confirmation."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Legrand EcoMeter",
        data={
            "auth_implementation": "netatmo",
            "token": {
                "access_token": "old-access-token",
                "refresh_token": "old-refresh-token",
            },
            "username": "user@example.com",
            "password": "password",
            "web_token": "private-web-token",
        },
        source=config_entries.SOURCE_USER,
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "entry_id": entry.entry_id,
        },
        data=entry.data,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"


@pytest.mark.asyncio
async def test_oauth_reauth_updates_entry_and_preserves_private_auth(
    hass: HomeAssistant,
) -> None:
    """Test successful OAuth reauth preserves private authentication data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Legrand EcoMeter",
        data={
            "auth_implementation": "netatmo",
            "token": {
                "access_token": "old-access-token",
                "refresh_token": "old-refresh-token",
            },
            "username": "user@example.com",
            "password": "private-password",
            "web_token": "private-web-token",
            "refresh_token_web": "private-refresh-token",
            "laravel_session": "private-session",
        },
        source=config_entries.SOURCE_USER,
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)

    flow = LegrandEnergyConfigFlow()
    flow.hass = hass
    flow.context = {
        "source": config_entries.SOURCE_REAUTH,
        "entry_id": entry.entry_id,
    }

    oauth_data = {
        "auth_implementation": "netatmo",
        "token": {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
        },
    }

    result = await flow.async_oauth_create_entry(oauth_data)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"

    # OAuth data was replaced.
    assert entry.data["auth_implementation"] == "netatmo"
    assert entry.data["token"]["access_token"] == "new-access-token"
    assert entry.data["token"]["refresh_token"] == "new-refresh-token"

    # Private Home + Control authentication data was preserved.
    assert entry.data["username"] == "user@example.com"
    assert entry.data["password"] == "private-password"
    assert entry.data["web_token"] == "private-web-token"
    assert entry.data["refresh_token_web"] == "private-refresh-token"
    assert entry.data["laravel_session"] == "private-session"
