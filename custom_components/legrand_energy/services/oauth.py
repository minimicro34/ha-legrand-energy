"""OAuth authentication service for Legrand Energy."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import aiohttp

from ..const import OAUTH_TOKEN_URL
from ..models.auth import OAuthSession

API_TIMEOUT = aiohttp.ClientTimeout(total=30)


class OAuthServiceError(Exception):
    """Exception raised when an OAuth operation fails."""


class OAuthService:
    """Handle public Netatmo OAuth authentication."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        client_id: str,
        client_secret: str,
    ) -> None:
        """Initialize the OAuth authentication service."""
        self._session = session
        self._client_id = client_id
        self._client_secret = client_secret

    async def refresh(
        self,
        session: OAuthSession,
    ) -> OAuthSession:
        """Refresh an existing OAuth session."""
        try:
            async with self._session.post(
                OAUTH_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": session.refresh_token,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                timeout=API_TIMEOUT,
            ) as response:
                status = response.status
                data = await self._read_json_response(response)

        except OAuthServiceError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise OAuthServiceError(
                "Unable to refresh the Netatmo OAuth token"
            ) from err

        access_token = data.get("access_token")

        if status >= 400 or not isinstance(access_token, str):
            raise OAuthServiceError(
                f"OAuth token refresh failed with HTTP status {status}"
            )

        refresh_token = data.get("refresh_token")
        if not isinstance(refresh_token, str):
            refresh_token = session.refresh_token

        expires_in = data.get("expires_in")
        if not isinstance(expires_in, int):
            expires_in = session.expires_in

        token_type = data.get("token_type")
        if not isinstance(token_type, str):
            token_type = session.token_type

        return OAuthSession(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            obtained_at=datetime.now(UTC),
            token_type=token_type,
        )

    @staticmethod
    async def _read_json_response(
        response: aiohttp.ClientResponse,
    ) -> dict[str, Any]:
        """Read and validate an OAuth JSON response."""
        try:
            data = await response.json(content_type=None)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as err:
            raise OAuthServiceError(
                f"Invalid OAuth JSON response from {response.url}"
            ) from err

        if not isinstance(data, dict):
            raise OAuthServiceError(
                f"Unexpected OAuth response type from {response.url}: "
                f"{type(data).__name__}"
            )

        return data
