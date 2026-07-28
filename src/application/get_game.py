"""Use case: retrieve an existing chess game by id."""

from __future__ import annotations

import uuid

from src.domain.game import Game, GameNotFoundError
from src.domain.ports import GameRepository


class GetGameUseCase:
    """Returns a Game entity or raises :class:`GameNotFoundError`."""

    def __init__(self, repository: GameRepository) -> None:
        self._repo = repository

    async def execute(self, game_id: uuid.UUID) -> Game:
        game = await self._repo.get_by_id(game_id)
        if game is None:
            raise GameNotFoundError(game_id)
        return game