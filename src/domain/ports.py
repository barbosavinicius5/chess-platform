"""Port interfaces (abstract base classes) — pure domain, no adapters here."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

from src.domain.game import Game


class GameRepository(ABC):
    """Secondary port: persistence of Game entities."""

    @abstractmethod
    async def save(self, game: Game) -> None:
        """Persist a Game (insert or update)."""
        ...

    @abstractmethod
    async def get_by_id(self, game_id: uuid.UUID) -> Game | None:
        """Return the Game with the given id, or *None* if not found."""
        ...


class EventEmitter(ABC):
    """Secondary port: domain-event publishing."""

    @abstractmethod
    async def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        """Publish *event_name* with *payload*."""
        ...


class MetricsCounter(ABC):
    """Secondary port: metrics instrumentation."""

    @abstractmethod
    async def increment(self, metric_name: str) -> None:
        """Increment the counter identified by *metric_name* by 1."""
        ...