"""Authentication manager for Legrand Energy."""

from __future__ import annotations

from typing import Protocol

from .models.auth import AuthenticationState, OAuthSession, PrivateSession
from .services.oauth import OAuthService
from .services.private import PrivateAuthService


class AuthenticationStore(Protocol):
    """Persistence interface for authentication sessions."""

    async def async_save_oauth(self, session: OAuthSession) -> None:
        """Persist an OAuth session."""

    async def async_save_private(self, session: PrivateSession) -> None:
        """Persist a private session."""


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
        oauth_service: OAuthService,
        private_service: PrivateAuthService,
        state: AuthenticationState | None = None,
        store: AuthenticationStore | None = None,
    ) -> None:
        """Initialize the authentication manager."""
        self._oauth_service = oauth_service
        self._private_service = private_service
        self._state = state or AuthenticationState()
        self._store = store

    @property
    def state(self) -> AuthenticationState:
        """Return the complete authentication state."""
        return self._state

    @property
    def oauth(self) -> OAuthSession:
        """Return the current OAuth session."""
        session = self._state.oauth

        if session is None:
            raise OAuthAuthenticationUnavailableError(
                "OAuth authentication session is unavailable"
            )

        return session

    @property
    def private(self) -> PrivateSession:
        """Return the current private session."""
        session = self._state.private

        if session is None:
            raise PrivateAuthenticationUnavailableError(
                "Private authentication session is unavailable"
            )

        return session

    @property
    def access_token(self) -> str:
        """Return the current OAuth access token."""
        return self.oauth.access_token

    @property
    def refresh_token(self) -> str:
        """Return the current OAuth refresh token."""
        return self.oauth.refresh_token

    @property
    def authorization_headers(self) -> dict[str, str]:
        """Return public OAuth authorization headers."""
        return self.oauth.authorization_header

    @property
    def private_headers(self) -> dict[str, str]:
        """Return private API authorization headers."""
        return self.private.headers

    async def refresh_oauth(self) -> OAuthSession:
        """Refresh, persist and return the OAuth session."""
        refreshed_session = await self._oauth_service.refresh(self.oauth)

        self._state.oauth = refreshed_session

        if self._store is not None:
            await self._store.async_save_oauth(refreshed_session)

        return refreshed_session

    async def refresh_private(self) -> PrivateSession:
        """Refresh, persist and return the private authentication session."""
        session = self.private

        await self._private_service.refresh(session)

        if self._store is not None:
            await self._store.async_save_private(session)

        return session

    def set_oauth(self, session: OAuthSession) -> None:
        """Replace the OAuth authentication session."""
        self._state.oauth = session

    def set_private(self, session: PrivateSession) -> None:
        """Replace the private authentication session."""
        self._state.private = session

    def clear(self) -> None:
        """Clear all authentication state."""
        self._state.clear()
