"""Tests for the Legrand Energy config flow."""

from __future__ import annotations

import importlib
import sys
import types
from collections.abc import Generator
from unittest.mock import AsyncMock, Mock

import pytest

MODULE = "custom_components.legrand_energy.config_flow"


@pytest.fixture
def config_flow_module(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[types.ModuleType]:
    """Import config_flow with minimal Home Assistant stubs."""
    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []

    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.SOURCE_REAUTH = "reauth"
    config_entries.ConfigFlowResult = dict

    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = []

    oauth2_flow = types.ModuleType("homeassistant.helpers.config_entry_oauth2_flow")

    class AbstractOAuth2FlowHandler:
        """Minimal OAuth2 config flow base."""

        def __init_subclass__(cls, **kwargs: object) -> None:
            super().__init_subclass__()

        def __init__(self) -> None:
            self.source: str | None = None

    oauth2_flow.AbstractOAuth2FlowHandler = AbstractOAuth2FlowHandler

    selector = types.ModuleType("homeassistant.helpers.selector")

    class TextSelectorType:
        EMAIL = "email"
        PASSWORD = "password"

    class TextSelectorConfig:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    class TextSelector:
        def __init__(self, config: object) -> None:
            self.config = config

    selector.TextSelectorType = TextSelectorType
    selector.TextSelectorConfig = TextSelectorConfig
    selector.TextSelector = TextSelector

    aiohttp_client = types.ModuleType("homeassistant.helpers.aiohttp_client")
    aiohttp_client.async_get_clientsession = Mock()

    helpers.config_entry_oauth2_flow = oauth2_flow
    helpers.selector = selector

    authentication_store = types.ModuleType(
        "custom_components.legrand_energy.authentication_store"
    )
    authentication_store.PRIVATE_COOKIE_NAMES = {
        "refresh_token_web": "authnetatmocomrefresh_token",
        "laravel_session": "authnetatmocomlaravel_session",
    }

    const = types.ModuleType("custom_components.legrand_energy.const")
    const.DOMAIN = "legrand_energy"
    const.OAUTH_SCOPES = ("read_station",)

    services = types.ModuleType("custom_components.legrand_energy.services")
    services.__path__ = []

    private = types.ModuleType("custom_components.legrand_energy.services.private")

    class PrivateAuthService:
        pass

    class PrivateAuthServiceAuthenticationError(Exception):
        pass

    class PrivateAuthServiceError(Exception):
        pass

    private.PrivateAuthService = PrivateAuthService
    private.PrivateAuthServiceAuthenticationError = (
        PrivateAuthServiceAuthenticationError
    )
    private.PrivateAuthServiceError = PrivateAuthServiceError

    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)
    monkeypatch.setitem(
        sys.modules,
        "homeassistant.config_entries",
        config_entries,
    )
    monkeypatch.setitem(sys.modules, "homeassistant.helpers", helpers)
    monkeypatch.setitem(
        sys.modules,
        "homeassistant.helpers.config_entry_oauth2_flow",
        oauth2_flow,
    )
    monkeypatch.setitem(
        sys.modules,
        "homeassistant.helpers.selector",
        selector,
    )
    monkeypatch.setitem(
        sys.modules,
        "homeassistant.helpers.aiohttp_client",
        aiohttp_client,
    )
    monkeypatch.setitem(
        sys.modules,
        "custom_components.legrand_energy.authentication_store",
        authentication_store,
    )
    monkeypatch.setitem(
        sys.modules,
        "custom_components.legrand_energy.const",
        const,
    )
    monkeypatch.setitem(
        sys.modules,
        "custom_components.legrand_energy.services",
        services,
    )
    monkeypatch.setitem(
        sys.modules,
        "custom_components.legrand_energy.services.private",
        private,
    )

    monkeypatch.delitem(sys.modules, MODULE, raising=False)

    module = importlib.import_module(MODULE)

    yield module

    sys.modules.pop(MODULE, None)


@pytest.mark.asyncio
async def test_reauth_starts_confirmation(
    config_flow_module: types.ModuleType,
) -> None:
    """Test that reauth starts with a confirmation step."""
    flow = config_flow_module.LegrandEnergyConfigFlow()

    expected = {"type": "form", "step_id": "reauth_confirm"}
    flow.async_step_reauth_confirm = AsyncMock(return_value=expected)

    result = await flow.async_step_reauth(
        {"token": {"access_token": "old-token"}},
    )

    assert result == expected
    flow.async_step_reauth_confirm.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_reauth_confirmation_form(
    config_flow_module: types.ModuleType,
) -> None:
    """Test the OAuth reauth confirmation form."""
    flow = config_flow_module.LegrandEnergyConfigFlow()

    expected = {
        "type": "form",
        "step_id": "reauth_confirm",
    }
    flow.async_show_form = Mock(return_value=expected)

    result = await flow.async_step_reauth_confirm()

    assert result == expected
    flow.async_show_form.assert_called_once()

    call = flow.async_show_form.call_args
    assert call.kwargs["step_id"] == "reauth_confirm"


@pytest.mark.asyncio
async def test_reauth_confirmation_continues_to_oauth(
    config_flow_module: types.ModuleType,
) -> None:
    """Test that confirmation continues to the OAuth flow."""
    flow = config_flow_module.LegrandEnergyConfigFlow()

    expected = {"type": "external"}
    flow.async_step_user = AsyncMock(return_value=expected)

    result = await flow.async_step_reauth_confirm(user_input={})

    assert result == expected
    flow.async_step_user.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_reauth_user_step_checks_unique_id_mismatch(
    config_flow_module: types.ModuleType,
) -> None:
    """Test unique ID handling during OAuth reauth."""
    flow = config_flow_module.LegrandEnergyConfigFlow()
    flow.source = config_flow_module.SOURCE_REAUTH

    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_mismatch = Mock()
    flow._abort_if_unique_id_configured = Mock()

    expected = {"type": "external"}
    flow.async_step_pick_implementation = AsyncMock(return_value=expected)

    result = await flow.async_step_user()

    assert result == expected

    flow.async_set_unique_id.assert_awaited_once_with(config_flow_module.DOMAIN)
    flow._abort_if_unique_id_mismatch.assert_called_once_with()
    flow._abort_if_unique_id_configured.assert_not_called()
    flow.async_step_pick_implementation.assert_awaited_once_with(None)


@pytest.mark.asyncio
async def test_normal_user_step_rejects_duplicate_entry(
    config_flow_module: types.ModuleType,
) -> None:
    """Test unique ID handling during normal setup."""
    flow = config_flow_module.LegrandEnergyConfigFlow()
    flow.source = "user"

    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_mismatch = Mock()
    flow._abort_if_unique_id_configured = Mock()

    expected = {"type": "external"}
    flow.async_step_pick_implementation = AsyncMock(return_value=expected)

    result = await flow.async_step_user()

    assert result == expected

    flow._abort_if_unique_id_configured.assert_called_once_with()
    flow._abort_if_unique_id_mismatch.assert_not_called()


@pytest.mark.asyncio
async def test_oauth_reauth_updates_existing_entry(
    config_flow_module: types.ModuleType,
) -> None:
    """Test successful OAuth reauth updates and reloads the entry."""
    flow = config_flow_module.LegrandEnergyConfigFlow()
    flow.source = config_flow_module.SOURCE_REAUTH

    entry = object()
    oauth_data = {
        "auth_implementation": "netatmo",
        "token": {
            "access_token": "new-token",
            "refresh_token": "new-refresh-token",
        },
    }

    flow._get_reauth_entry = Mock(return_value=entry)

    expected = {
        "type": "abort",
        "reason": "reauth_successful",
    }
    flow.async_update_reload_and_abort = Mock(return_value=expected)

    result = await flow.async_oauth_create_entry(oauth_data)

    assert result == expected

    flow.async_update_reload_and_abort.assert_called_once_with(
        entry,
        data_updates=oauth_data,
    )


@pytest.mark.asyncio
async def test_initial_oauth_continues_to_private_auth(
    config_flow_module: types.ModuleType,
) -> None:
    """Test initial OAuth setup continues to private authentication."""
    flow = config_flow_module.LegrandEnergyConfigFlow()
    flow.source = "user"

    oauth_data = {
        "auth_implementation": "netatmo",
        "token": {
            "access_token": "access-token",
        },
    }

    expected = {
        "type": "form",
        "step_id": "private",
    }
    flow.async_step_private = AsyncMock(return_value=expected)

    result = await flow.async_oauth_create_entry(oauth_data)

    assert result == expected
    assert flow._oauth_data == oauth_data

    flow.async_step_private.assert_awaited_once_with()
