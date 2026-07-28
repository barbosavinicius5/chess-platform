from __future__ import annotations

from chess.application.ports.game_repository import GameRepository
from chess.domain.game import Game


class GameNotFound(Exception): ...


class AccessDenied(Exception): ...


class GetGameUseCase:
    def __init__(self, repo: GameRepository) -> None:
        self._repo = repo

    async def execute(self, game_id: str, player_id: str) -> Game:
        game = await self._repo.get_by_id(game_id)
        if game is None:
            raise GameNotFound(game_id)
        if not game.is_participant(player_id):
            raise AccessDenied(player_id)
        return game