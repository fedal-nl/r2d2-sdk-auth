"""SDK-specific exceptions."""


class R2D2Error(Exception):
    """An R2D2 API request failed."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(R2D2Error):
    """Authentication is missing, invalid, or expired."""
