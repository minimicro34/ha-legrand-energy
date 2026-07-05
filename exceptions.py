class LegrandError(Exception):
    """Base exception."""


class AuthenticationError(LegrandError):
    """Authentication failed."""


class ApiError(LegrandError):
    """API error."""
