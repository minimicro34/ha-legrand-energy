"""Authentication manager for Legrand Energy."""

from __future__ import annotations

import logging
from typing import Any, Protocol

import aiohttp
from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session

from .models.auth import PrivateSession

_LOGGER = logging.getLogger(__name__)


class AuthenticationStore(Protocol):
    """Persistence interface for private authentication sessions."""

    async def async_save_private(
        self,
        session: PrivateSession,
    ) -> None:
        """Persist a private session."""


class PrivateAuthenticationService(Protocol):
    """Interface for private Netatmo authentication."""

    async def login(
        self,
        username: str,
        password: str,
    ) -> PrivateSession:
        """Create and return a private authentication session."""

    async def refresh(
        self,
        session: PrivateSession,
    ) -> None:
        """Refresh a private authentication session."""


class AuthenticationError(Exception):
    """Base authentication manager error."""


class OAuthAuthenticationUnavailableError(AuthenticationError):
    """OAuth authentication state is unavailable."""


class PrivateAuthenticationUnavailableError(AuthenticationError):
    """Private authentication state is unavailable."""


class AuthenticationManager:
    """Manage public and private Netatmo authentication state."""

    def __init__(
        self,
        oauth_session: OAuth2Session,
        private_service: PrivateAuthenticationService,
        private_session: PrivateSession | None,
        store: AuthenticationStore,
    ) -> None:
        """Initialize the authentication manager."""
        self._oauth_session = oauth_session
        self._private_service = private_service
        self._private = private_session
        self._store = store

    @property
    def private(self) -> PrivateSession:
        """Return the current private session."""
        if self._private is None:
            raise PrivateAuthenticationUnavailableError(
                "Private authentication session is unavailable"
            )

        return self._private

    @property
    def oauth_token(self) -> dict[str, Any]:
        """Return the current Home Assistant OAuth token data."""
        token = self._oauth_session.token

        if not isinstance(token, dict):
            raise OAuthAuthenticationUnavailableError(
                "OAuth authentication token is unavailable"
            )

        return token

    @property
    def access_token(self) -> str:
        """Return the current OAuth access token."""
        access_token = self.oauth_token.get("access_token")

        if not isinstance(access_token, str) or not access_token:
            raise OAuthAuthenticationUnavailableError(
                "OAuth access token is unavailable"
            )

        return access_token

    @property
    def authorization_headers(self) -> dict[str, str]:
        """Return public OAuth authorization headers."""
        token_type = self.oauth_token.get("token_type", "Bearer")

        if not isinstance(token_type, str) or not token_type:
            token_type = "Bearer"

        return {
            "Authorization": f"{token_type} {self.access_token}",
        }

    @property
    def private_headers(self) -> dict[str, str]:
        """Return private API authorization headers."""
        return self.private.headers

    async def async_ensure_oauth_valid(self) -> None:
        """Ensure that the OAuth token is valid."""
        try:
            await self._oauth_session.async_ensure_token_valid()
        except aiohttp.ClientError as err:
            raise AuthenticationError("Unable to refresh the OAuth token") from err

    async def login_private(
        self,
        username: str,
        password: str,
    ) -> PrivateSession:
        """Create, persist and return a private authentication session."""
        session = await self._private_service.login(
            username=username,
            password=password,
        )

        self._private = session
        await self._store.async_save_private(session)

        return session

    async def refresh_private(self) -> PrivateSession:
        """Refresh, persist and return the private authentication session."""
        session = self.private
        old_token = session.web_token

        await self._private_service.refresh(session)

        _LOGGER.debug(
            "Private session refreshed (changed=%s, old=%s...%s, new=%s...%s)",
            old_token != session.web_token,
            old_token[:8],
            old_token[-8:],
            session.web_token[:8],
            session.web_token[-8:],
        )

        await self._store.async_save_private(session)

        return session

    def set_private(self, session: PrivateSession) -> None:
        """Replace the private authentication session."""
        self._private = session

    def clear(self) -> None:
        """Clear the private authentication state."""
        self._private = None
