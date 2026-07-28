"""Domain exceptions — no framework dependencies (stdlib only)."""


class LinkNotFoundError(Exception):
    """Raised when a short_code does not exist in the repository."""

    def __init__(self, short_code: str) -> None:
        super().__init__(f"Link not found: {short_code!r}")
        self.short_code = short_code
