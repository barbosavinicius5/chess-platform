"""ConnectionManager — tracks active WebSocket connections per game_id."""

import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Thread-safe (asyncio-safe) registry of WebSocket connections.

    Connections are grouped by *game_id* so that broadcasts can be
    scoped to a single game channel.
    """

    def __init__(self) -> None:
        # game_id -> list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    def connect(self, game_id: str, websocket: WebSocket) -> None:
        """Register *websocket* as a participant of *game_id*."""
        self._connections[game_id].append(websocket)
        logger.debug("ws.connected", extra={"game_id": game_id, "total": len(self._connections[game_id])})

    def disconnect(self, game_id: str, websocket: WebSocket) -> None:
        """Remove *websocket* from the *game_id* connection list."""
        connections = self._connections.get(game_id, [])
        if websocket in connections:
            connections.remove(websocket)
        logger.debug("ws.disconnected", extra={"game_id": game_id, "total": len(connections)})

    async def broadcast(self, game_id: str, message: str) -> None:
        """Send *message* (JSON string) to every connection in *game_id*.

        Gracefully handles 0 or 1 connections — never raises.
        Stale connections are silently removed on send failure.
        """
        connections = list(self._connections.get(game_id, []))
        if not connections:
            logger.debug("ws.broadcast.no_connections", extra={"game_id": game_id})
            return

        dead: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:  # noqa: BLE001
                logger.warning("ws.broadcast.send_failed", extra={"game_id": game_id})
                dead.append(ws)

        # Clean up stale connections
        for ws in dead:
            self.disconnect(game_id, ws)

        logger.debug(
            "ws.broadcast.done",
            extra={"game_id": game_id, "recipients": len(connections) - len(dead)},
        )
