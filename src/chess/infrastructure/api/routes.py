"""FastAPI routes — REST helpers + WebSocket live channel."""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from chess.application.services import GameService
from chess.domain.models import Move
from chess.infrastructure.websocket.adapter import WebSocketNotifier
from chess.infrastructure.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared singletons (created once at import time; overridable in tests)
# ---------------------------------------------------------------------------
connection_manager = ConnectionManager()
_notifier = WebSocketNotifier(connection_manager)
game_service = GameService(_notifier)

router = APIRouter()


# ---------------------------------------------------------------------------
# REST helpers (thin — mainly useful for integration tests / demo)
# ---------------------------------------------------------------------------


class CreateGameRequest(BaseModel):
    game_id: str
    white_player_id: str
    black_player_id: str


class SubmitMoveRequest(BaseModel):
    uci: str
    player_id: str


@router.post("/games", status_code=201)
async def create_game(body: CreateGameRequest) -> dict[str, str]:
    game = game_service.create_game(body.game_id, body.white_player_id, body.black_player_id)
    return {"game_id": game.game_id, "fen": game.fen, "status": game.status}


@router.post("/games/{game_id}/moves", status_code=200)
async def submit_move(game_id: str, body: SubmitMoveRequest) -> dict[str, str]:
    move = Move(uci=body.uci, player_id=body.player_id)
    result = await game_service.submit_move(game_id, move)
    return {"result": result.value}


# ---------------------------------------------------------------------------
# WebSocket — live channel
# ---------------------------------------------------------------------------


@router.websocket("/games/{game_id}/live")
async def ws_live(websocket: WebSocket, game_id: str) -> None:
    """WebSocket endpoint — clients connect here to receive live FEN updates."""
    await websocket.accept()
    connection_manager.connect(game_id, websocket)
    logger.info("ws.client_connected", extra={"game_id": game_id})

    try:
        while True:
            # Keep the connection alive; clients are passive receivers.
            # A real implementation would handle client-sent messages here.
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(game_id, websocket)
        logger.info("ws.client_disconnected", extra={"game_id": game_id})
