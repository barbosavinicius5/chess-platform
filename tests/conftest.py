from __future__ import annotations

import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from chess.infrastructure.db.models import Base, GameModel, MoveModel
from chess.infrastructure.db.session import get_db
from chess.infrastructure.main import app

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


async def create_game(
    session: AsyncSession,
    *,
    status: str = "in_progress",
    white_player_id: str | None = None,
    black_player_id: str | None = None,
    fen: str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    turn: str = "brancas",
    moves: list[tuple[str, int]] | None = None,
) -> GameModel:
    game_id = str(uuid.uuid4())
    white_player_id = white_player_id or str(uuid.uuid4())

    game = GameModel(
        id=game_id,
        status=status,
        white_player_id=white_player_id,
        black_player_id=black_player_id,
        fen=fen,
        turn=turn,
    )
    session.add(game)
    await session.flush()

    if moves:
        for san, order in moves:
            move = MoveModel(
                id=str(uuid.uuid4()),
                game_id=game_id,
                san=san,
                order=order,
            )
            session.add(move)

    await session.commit()
    return game