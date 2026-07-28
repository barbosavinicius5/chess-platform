from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from chess.application.use_cases.get_game import GetGameUseCase
from chess.infrastructure.db.session import get_db
from chess.infrastructure.repositories.game_repository import SQLAlchemyGameRepository


async def get_player_id(x_player_id: str = Header(..., alias="X-Player-Id")) -> str:
    return x_player_id


async def get_game_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLAlchemyGameRepository:
    return SQLAlchemyGameRepository(session)


async def get_get_game_use_case(
    repo: SQLAlchemyGameRepository = Depends(get_game_repo),
) -> GetGameUseCase:
    return GetGameUseCase(repo)