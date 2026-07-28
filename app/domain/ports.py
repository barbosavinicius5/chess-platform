"""Domain ports (interfaces) — no framework dependencies (stdlib only)."""

from abc import ABC, abstractmethod

from app.domain.entities import Link


class LinkRepository(ABC):
    """Port: persistence contract for Link aggregate."""

    @abstractmethod
    async def get_by_short_code(self, short_code: str) -> Link | None:
        """Return the Link for *short_code*, or None if not found."""

    @abstractmethod
    async def save(self, link: Link) -> Link:
        """Persist a new Link and return it (with any DB-generated fields)."""

    @abstractmethod
    async def increment_clicks(self, short_code: str) -> int:
        """Atomically increment clicks counter and return the new value."""

    @abstractmethod
    async def get_stats(self, short_code: str) -> int | None:
        """Return current clicks count for *short_code*, or None if not found."""
