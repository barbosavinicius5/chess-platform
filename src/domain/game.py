"""Domain entities, value objects and exceptions for the chess platform."""

from __future__ import annotations

import uuid
from enum import StrEnum

INITIAL_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


class GameState(StrEnum):
    waiting = "waiting"
    in_progress = "in_progress"
    finished = "finished"


class Game:
    """Core domain entity — no framework dependencies."""

    def __init__(
        self,
        game_id: uuid.UUID,
        estado: GameState,
        fen: str,
    ) -> None:
        self.game_id = game_id
        self.estado = estado
        self.fen = fen

    @classmethod
    def create_new(cls) -> Game:
        """Factory: creates a brand-new game in the *waiting* state."""
        return cls(
            game_id=uuid.uuid4(),
            estado=GameState.waiting,
            fen=INITIAL_FEN,
        )

    def __repr__(self) -> str:
        return f"Game(game_id={self.game_id}, estado={self.estado}, fen={self.fen!r})"


class GameNotFoundError(Exception):
    """Raised when a game cannot be found by its id."""

    def __init__(self, game_id: uuid.UUID) -> None:
        super().__init__(f"Partida não encontrada: {game_id}")
        self.game_id = game_id
