"""Authentication manager for Legrand Energy."""

from __future__ import annotations

from typing import Any, Protocol

from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session

from .models.auth import AuthenticationState, PrivateSession
from .services.private import PrivateAuthService


class AuthenticationStore(Protocol):
    """Persistence interface for private authentication sessions."""

    async def async_save_private(
        self,
        session: PrivateSession,
    ) -> None:
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
        oauth_session: OAuth2Session,
        private_service: PrivateAuthService,
        state: AuthenticationState | None = None,
        store: AuthenticationStore | None = None,
    ) -> None:
        """Initialize the authentication manager."""
        self._oauth_session = oauth_session
        self._private_service = private_service
        self._state = state or AuthenticationState()
        self._store = store

    @property
    def state(self) -> AuthenticationState:
        """Return the private authentication state."""
        return self._state

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
    def refresh_token(self) -> str:
        """Return the current OAuth refresh token."""
        refresh_token = self.oauth_token.get("refresh_token")

        if not isinstance(refresh_token, str) or not refresh_token:
            raise OAuthAuthenticationUnavailableError(
                "OAuth refresh token is unavailable"
            )

        return refresh_token

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
        """Ensure that the Home Assistant OAuth token is valid."""
        await self._oauth_session.async_ensure_token_valid()

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

        self._state.private = session

        if self._store is not None:
            await self._store.async_save_private(session)

        return session

    async def refresh_private(self) -> PrivateSession:
        """Refresh, persist and return the private authentication session."""
        session = self.private

        await self._private_service.refresh(session)

        if self._store is not None:
            await self._store.async_save_private(session)

        return session

    def set_private(self, session: PrivateSession) -> None:
        """Replace the private authentication session."""
        self._state.private = session

    def clear(self) -> None:
        """Clear authentication state."""
        self._state.clear()
