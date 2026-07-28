"""Domain output ports (interfaces).

The domain defines the *shape* of collaborators it needs; the concrete
implementations live in the infrastructure layer.
"""

from abc import ABC, abstractmethod


class IGameNotifier(ABC):
    """Output port: notify connected clients about a game state change."""

    @abstractmethod
    async def notify_move_accepted(self, game_id: str, fen: str) -> None:
        """Broadcast the new FEN to all clients watching *game_id*."""
        ...
