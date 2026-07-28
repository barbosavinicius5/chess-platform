"""SQLAlchemy async adapter implementing GameRepository port."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.game import Game, GameState
from src.domain.ports import GameRepository
from src.infrastructure.models import GameModel


class AsyncGameRepository(GameRepository):
    """Concrete repository backed by a PostgreSQL database via SQLAlchemy async."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, game: Game) -> None:
        model = GameModel(
            game_id=game.game_id,
            estado=game.estado.value,
            fen=game.fen,
        )
        self._session.add(model)
        await self._session.commit()

    async def get_by_id(self, game_id: uuid.UUID) -> Game | None:
        result = await self._session.execute(select(GameModel).where(GameModel.game_id == game_id))
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return Game(
            game_id=model.game_id,
            estado=GameState(model.estado),
            fen=model.fen,
        )