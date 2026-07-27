"""Authentication models for Legrand Energy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass(slots=True)
class AuthenticationState:
    """Current authentication state."""

    oauth: OAuthSession | None = None
    private: PrivateSession | None = None

    def clear(self) -> None:
        """Clear all authentication sessions."""
        self.oauth = None
        self.private = None


@dataclass(slots=True)
class OAuthSession:
    """OAuth authentication session."""

    access_token: str
    refresh_token: str
    expires_in: int
    obtained_at: datetime
    token_type: str = "Bearer"

    @property
    def expires_at(self) -> datetime:
        """Return token expiration datetime."""
        return self.obtained_at + timedelta(seconds=self.expires_in)

    @property
    def remaining(self) -> timedelta:
        """Return remaining token lifetime."""
        return self.expires_at - datetime.now(tz=self.obtained_at.tzinfo)

    @property
    def expired(self) -> bool:
        """Return whether the token has expired or is about to expire."""
        return self.remaining <= timedelta(seconds=60)

    @property
    def authorization_header(self) -> dict[str, str]:
        """Return OAuth authorization headers."""
        return {
            "Authorization": f"{self.token_type} {self.access_token}",
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize the OAuth session."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_in": self.expires_in,
            "obtained_at": self.obtained_at.isoformat(),
            "token_type": self.token_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OAuthSession:
        """Deserialize an OAuth session."""
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=data["expires_in"],
            obtained_at=datetime.fromisoformat(data["obtained_at"]),
            token_type=data.get("token_type", "Bearer"),
        )


@dataclass(slots=True)
class PrivateSession:
    """Current authenticated private Netatmo session."""

    web_token: str
    cookies: dict[str, str]

    @property
    def headers(self) -> dict[str, str]:
        """Return headers for authenticated private API requests."""
        return {
            "Authorization": f"Bearer {self.web_token}",
            "Accept": "application/json",
        }
