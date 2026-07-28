from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from chess.domain.game import Game, GameStatus, Move, Side
from chess.infrastructure.db.models import GameModel


class SQLAlchemyGameRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, game_id: str) -> Game | None:
        stmt = (
            select(GameModel)
            .where(GameModel.id == game_id)
            .options(selectinload(GameModel.moves))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        moves = [
            Move(san=m.san, order=m.order)
            for m in sorted(model.moves, key=lambda x: x.order)
        ]

        return Game(
            game_id=model.id,
            status=GameStatus(model.status),
            white_player_id=model.white_player_id,
            black_player_id=model.black_player_id,
            fen=model.fen,
            turn=Side(model.turn),
            moves=moves,
        )