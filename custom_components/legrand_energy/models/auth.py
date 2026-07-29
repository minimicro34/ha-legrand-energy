"""Authentication models for Legrand Energy."""

from __future__ import annotations

from dataclasses import dataclass


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
