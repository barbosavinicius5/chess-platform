"""Domain models for chess platform.

Pure Python dataclasses — no SQLAlchemy, no FastAPI, no I/O.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class GameStatus(StrEnum):
    WAITING = "waiting"
    ONGOING = "ongoing"
    FINISHED = "finished"


class MoveResult(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass
class Move:
    """Represents a single chess move in UCI notation (e.g. 'e2e4')."""

    uci: str
    player_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Game:
    """Aggregate root — holds the authoritative FEN state of a chess game."""

    game_id: str = field(default_factory=lambda: str(uuid4()))
    white_player_id: str = ""
    black_player_id: str = ""
    # Starting position FEN (standard chess opening)
    fen: str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    status: GameStatus = GameStatus.WAITING
    move_history: list[Move] = field(default_factory=list)

    def apply_move(self, move: Move) -> MoveResult:
        """Validate and apply a move; update FEN on success.

        For this task the validation is intentionally minimal — a real
        implementation would use a chess engine (python-chess).  The rule
        here: a move is *accepted* when the game is ONGOING and the piece
        notation is non-empty.
        """
        if self.status != GameStatus.ONGOING:
            return MoveResult.REJECTED
        if not move.uci or not move.uci.strip():
            return MoveResult.REJECTED

        # Minimal FEN update: append move counter to simulate state change.
        # A production system would delegate to python-chess here.
        parts = self.fen.split()
        # Toggle active color
        parts[1] = "b" if parts[1] == "w" else "w"
        self.fen = " ".join(parts)
        self.move_history.append(move)
        return MoveResult.ACCEPTED