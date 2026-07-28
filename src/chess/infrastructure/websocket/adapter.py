"""WebSocketNotifier — infrastructure adapter that implements IGameNotifier."""

import json
import logging
import time
from datetime import UTC, datetime

from chess.domain.ports import IGameNotifier
from chess.infrastructure.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


class WebSocketNotifier(IGameNotifier):
    """Concrete implementation of IGameNotifier using FastAPI WebSockets.

    Responsibilities:
    - Build the ``lance_propagado`` JSON payload.
    - Broadcast to all connections via ConnectionManager.
    - Measure and log propagation latency.
    - Emit a structured JSON analytics event.
    """

    def __init__(self, connection_manager: ConnectionManager) -> None:
        self._manager = connection_manager

    async def notify_move_accepted(self, game_id: str, fen: str) -> None:
        """Fan-out accepted move FEN to all clients watching *game_id*."""
        start = time.monotonic()
        now = datetime.now(UTC)

        payload = {
            "type": "lance_propagado",
            "game_id": game_id,
            "fen": fen,
            "timestamp": now.isoformat(),
        }
        message = json.dumps(payload)

        await self._manager.broadcast(game_id, message)

        latencia_ms = (time.monotonic() - start) * 1000

        # Structured JSON analytics event (mandatory per spec)
        logger.info(
            "lance_propagado",
            extra={
                "event": "lance_propagado",
                "game_id": game_id,
                "fen": fen,
                "latencia_propagacao_ms": round(latencia_ms, 3),
                "timestamp": now.isoformat(),
            },
        )
