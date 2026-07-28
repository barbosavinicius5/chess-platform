"""Domain entities — no framework dependencies (stdlib only)."""

from dataclasses import dataclass, field


@dataclass
class Link:
    """Represents a shortened URL link."""

    short_code: str
    original_url: str
    clicks: int = field(default=0)
