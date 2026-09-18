"""Tests for the private Netatmo authentication service."""

from __future__ import annotations

from http.cookies import SimpleCookie
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from yarl import URL

from custom_components.legrand_energy.models.auth import PrivateSession
from custom_components.legrand_energy.services.private import (
    ACCESS_TOKEN_COOKIE,
    DEFAULT_REFRESH_COOKIES,
    REQUIRED_REFRESH_COOKIES,
    PrivateAuthService,
    PrivateAuthServiceAuthenticationError,
    PrivateAuthServiceCsrfError,
    PrivateAuthServiceInvalidCredentialsError,
    PrivateAuthServiceSessionError,
)


def _cookies(**values: str) -> dict[str, str]:
    return {name: values.get(name, f"value-{index}") for index, name in enumerate(REQUIRED_REFRESH_COOKIES)}


def _response(status: int = 200, *, location: str | None = None, url: str = "https://auth.netatmo.com/access/keychain"):
    response = MagicMock()
    response.status = status
    response.headers = {} if location is None else {"Location": location}
    response.url = URL(url)
    response.cookies = SimpleCookie()
    return response


def _context(response):
    context = AsyncMock()
    context.__aenter__.return_value = response
    return context


@pytest.mark.asyncio
async def test_get_csrf_success_and_errors() -> None:
    session = MagicMock()
    response = _response()
    response.json = AsyncMock(return_value={"token": "csrf-token"})
    session.get.return_value = _context(response)
    service = PrivateAuthService(session)
    assert await service._get_csrf() == "csrf-token"

    response.status = 503
    with pytest.raises(PrivateAuthServiceCsrfError, match="HTTP status 503"):
        await service._get_csrf()

    response.status = 200
    response.json = AsyncMock(return_value={})
    with pytest.raises(PrivateAuthServiceCsrfError, match="valid token"):
        await service._get_csrf()


@pytest.mark.asyncio
async def test_post_login_success_and_failures() -> None:
    session = MagicMock()
    response = _response(status=302, location="/access/keychain?foo=bar")
    session.post.return_value = _context(response)
    service = PrivateAuthService(session)

    redirect = await service._post_login("user@example.com", "secret", "csrf")
    assert "/access/keychain" in redirect

    response.status = 401
    with pytest.raises(PrivateAuthServiceInvalidCredentialsError):
        await service._post_login("user@example.com", "bad", "csrf")

    response.status = 200
    with pytest.raises(PrivateAuthServiceInvalidCredentialsError):
        await service._post_login("user@example.com", "bad", "csrf")

    response.status = 500
    with pytest.raises(PrivateAuthServiceAuthenticationError, match="HTTP status 500"):
        await service._post_login("user@example.com", "secret", "csrf")

    response.status = 302
    response.headers = {}
    with pytest.raises(PrivateAuthServiceSessionError, match="redirect URL"):
        await service._post_login("user@example.com", "secret", "csrf")

    response.headers = {"Location": "/access/login"}
    with pytest.raises(PrivateAuthServiceInvalidCredentialsError, match="keychain"):
        await service._post_login("user@example.com", "secret", "csrf")


@pytest.mark.asyncio
async def test_complete_keychain() -> None:
    session = MagicMock()
    response = _response()
    session.get.return_value = _context(response)
    service = PrivateAuthService(session)

    await service._complete_keychain("https://auth.netatmo.com/access/keychain")

    response.status = 500
    with pytest.raises(PrivateAuthServiceSessionError, match="HTTP status 500"):
        await service._complete_keychain("https://auth.netatmo.com/access/keychain")

    response.status = 200
    response.url = URL("https://home.netatmo.com/control/dashboard")
    with pytest.raises(PrivateAuthServiceSessionError, match="unexpected page"):
        await service._complete_keychain("https://auth.netatmo.com/access/keychain")


def test_extract_session_cookies_and_web_token() -> None:
    session = MagicMock()
    service = PrivateAuthService(session)
    cookies = _cookies()
    session.cookie_jar.filter_cookies.return_value = SimpleCookie(cookies)

    assert service._extract_session_cookies() == cookies

    missing = dict(cookies)
    missing.pop(REQUIRED_REFRESH_COOKIES[0])
    session.cookie_jar.filter_cookies.return_value = SimpleCookie(missing)
    with pytest.raises(PrivateAuthServiceSessionError, match="missing required"):
        service._extract_session_cookies()

    valid_token = "abcdefghijklmnopqrstuvwxyz"
    assert service._extract_web_token({ACCESS_TOKEN_COOKIE: valid_token}) == valid_token
    assert service._extract_web_token({ACCESS_TOKEN_COOKIE: "abc%2Ddefghijklmnopqrstuvwxyz"}) == "abc-defghijklmnopqrstuvwxyz"

    with pytest.raises(PrivateAuthServiceSessionError, match="invalid web access token"):
        service._extract_web_token({ACCESS_TOKEN_COOKIE: "short"})


@pytest.mark.asyncio
async def test_login_composes_private_session() -> None:
    service = PrivateAuthService(MagicMock())
    cookies = _cookies()
    with (
        patch.object(service, "_get_csrf", new=AsyncMock(return_value="csrf")),
        patch.object(
            service,
            "_post_login",
            new=AsyncMock(return_value="https://auth.netatmo.com/access/keychain"),
        ),
        patch.object(service, "_complete_keychain", new=AsyncMock()),
        patch.object(service, "_extract_session_cookies", return_value=cookies),
        patch.object(service, "_extract_web_token", return_value="web-token"),
    ):
        result = await service.login("user@example.com", "secret")

    assert result == PrivateSession(web_token="web-token", cookies=cookies)


def test_refresh_cookie_helpers() -> None:
    service = PrivateAuthService(MagicMock())
    session = PrivateSession(web_token="old-token", cookies=_cookies())

    assert service._can_refresh(session) is True
    built = service._build_refresh_cookies(session)
    assert all(built[name] == session.cookies[name] for name in REQUIRED_REFRESH_COOKIES)
    assert all(built[name] == value for name, value in DEFAULT_REFRESH_COOKIES.items())

    session.cookies.pop(REQUIRED_REFRESH_COOKIES[0])
    assert service._can_refresh(session) is False

    rotated = SimpleCookie()
    rotated[REQUIRED_REFRESH_COOKIES[1]] = "rotated"
    rotated[REQUIRED_REFRESH_COOKIES[2]] = "deleted"
    service._update_rotated_cookies(session, rotated)
    assert session.cookies[REQUIRED_REFRESH_COOKIES[1]] == "rotated"
    assert REQUIRED_REFRESH_COOKIES[2] not in session.cookies


@pytest.mark.asyncio
async def test_refresh_success_and_failures() -> None:
    aiohttp_session = MagicMock()
    response = _response(status=302)
    response.cookies[ACCESS_TOKEN_COOKIE] = "abcdefghijklmnopqrstuvwxyz"
    aiohttp_session.get.return_value = _context(response)
    service = PrivateAuthService(aiohttp_session)
    private_session = PrivateSession(web_token="old-token", cookies=_cookies())

    await service.refresh(private_session)
    assert private_session.web_token == "abcdefghijklmnopqrstuvwxyz"

    incomplete = PrivateSession(web_token="old-token", cookies={})
    with pytest.raises(PrivateAuthServiceAuthenticationError, match="incomplete"):
        await service.refresh(incomplete)

    private_session = PrivateSession(web_token="old-token", cookies=_cookies())
    response.status = 500
    with pytest.raises(PrivateAuthServiceAuthenticationError, match="HTTP status 500"):
        await service.refresh(private_session)

    response.status = 302
    response.headers = {"Location": "/access/login"}
    with pytest.raises(PrivateAuthServiceAuthenticationError, match="login page"):
        await service.refresh(private_session)

    response.headers = {}
    response.cookies = SimpleCookie()
    with pytest.raises(PrivateAuthServiceAuthenticationError, match="new access token"):
        await service.refresh(private_session)
