from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List

INITIAL_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


class GameStatus(str, Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class Side(str, Enum):
    WHITE = "brancas"
    BLACK = "pretas"


@dataclass
class Move:
    san: str
    order: int


@dataclass
class Game:
    game_id: str
    status: GameStatus
    white_player_id: str
    black_player_id: str | None
    fen: str = INITIAL_FEN
    turn: Side = Side.WHITE
    moves: List[Move] = field(default_factory=list)

    def is_participant(self, player_id: str) -> bool:
        return player_id in (self.white_player_id, self.black_player_id)