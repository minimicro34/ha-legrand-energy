"""Tests for the Legrand Energy authentication manager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.legrand_energy.authentication import (
    AuthenticationError,
    AuthenticationManager,
    OAuthAuthenticationUnavailableError,
    PrivateAuthenticationUnavailableError,
)
from custom_components.legrand_energy.models.auth import PrivateSession


def _manager(
    *,
    token: object = None,
    private_session: PrivateSession | None = None,
) -> tuple[AuthenticationManager, MagicMock, MagicMock, MagicMock]:
    oauth_session = MagicMock()
    oauth_session.token = (
        {"access_token": "access-token", "token_type": "Bearer"}
        if token is None
        else token
    )
    oauth_session.async_ensure_token_valid = AsyncMock()

    private_service = MagicMock()
    private_service.login = AsyncMock()
    private_service.refresh = AsyncMock()

    store = MagicMock()
    store.async_save_private = AsyncMock()

    manager = AuthenticationManager(
        oauth_session=oauth_session,
        private_service=private_service,
        private_session=private_session,
        store=store,
    )
    return manager, oauth_session, private_service, store


def test_private_session_properties_and_state() -> None:
    session = PrivateSession(web_token="private-token", cookies={"cookie": "value"})
    manager, _, _, _ = _manager(private_session=session)

    assert manager.private is session
    assert manager.private_headers == session.headers

    replacement = PrivateSession(web_token="replacement", cookies={})
    manager.set_private(replacement)
    assert manager.private is replacement

    manager.clear()
    with pytest.raises(
        PrivateAuthenticationUnavailableError, match="session is unavailable"
    ):
        manager.private


def test_oauth_properties() -> None:
    manager, _, _, _ = _manager()
    assert manager.oauth_token["access_token"] == "access-token"
    assert manager.access_token == "access-token"
    assert manager.authorization_headers == {
        "Authorization": "Bearer access-token"
    }

    manager, _, _, _ = _manager(
        token={"access_token": "access-token", "token_type": "Custom"}
    )
    assert manager.authorization_headers == {
        "Authorization": "Custom access-token"
    }

    manager, _, _, _ = _manager(
        token={"access_token": "access-token", "token_type": ""}
    )
    assert manager.authorization_headers == {
        "Authorization": "Bearer access-token"
    }


def test_oauth_property_errors() -> None:
    manager, _, _, _ = _manager(token="invalid")
    with pytest.raises(
        OAuthAuthenticationUnavailableError, match="token is unavailable"
    ):
        manager.oauth_token

    for token in ({}, {"access_token": ""}, {"access_token": 123}):
        manager, _, _, _ = _manager(token=token)
        with pytest.raises(
            OAuthAuthenticationUnavailableError, match="access token is unavailable"
        ):
            manager.access_token


@pytest.mark.asyncio
async def test_ensure_oauth_valid() -> None:
    manager, oauth_session, _, _ = _manager()
    await manager.async_ensure_oauth_valid()
    oauth_session.async_ensure_token_valid.assert_awaited_once()

    oauth_session.async_ensure_token_valid.side_effect = aiohttp.ClientError("network")
    with pytest.raises(AuthenticationError, match="Unable to refresh"):
        await manager.async_ensure_oauth_valid()


@pytest.mark.asyncio
async def test_login_private_persists_session() -> None:
    manager, _, private_service, store = _manager()
    session = PrivateSession(web_token="private-token", cookies={})
    private_service.login.return_value = session

    result = await manager.login_private("user@example.com", "password")

    assert result is session
    assert manager.private is session
    private_service.login.assert_awaited_once_with(
        username="user@example.com",
        password="password",
    )
    store.async_save_private.assert_awaited_once_with(session)


@pytest.mark.asyncio
async def test_refresh_private_persists_updated_session() -> None:
    session = PrivateSession(
        web_token="old-token-12345678",
        cookies={"cookie": "value"},
    )
    manager, _, private_service, store = _manager(private_session=session)

    async def refresh(current: PrivateSession) -> None:
        current.web_token = "new-token-87654321"

    private_service.refresh.side_effect = refresh

    result = await manager.refresh_private()

    assert result is session
    assert session.web_token == "new-token-87654321"
    private_service.refresh.assert_awaited_once_with(session)
    store.async_save_private.assert_awaited_once_with(session)
