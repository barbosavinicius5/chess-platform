from __future__ import annotations

from pydantic import BaseModel


class GameResponse(BaseModel):
    game_id: str
    status: str
    turn: str
    fen: str
    moves: list[str]