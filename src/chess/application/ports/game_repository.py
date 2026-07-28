from __future__ import annotations

from typing import Protocol

from chess.domain.game import Game


class GameRepository(Protocol):
    async def get_by_id(self, game_id: str) -> Game | None: ...