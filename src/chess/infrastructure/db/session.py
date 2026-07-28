from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://chess:chess@localhost:5432/chess")

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncSession:  # type: ignore[return]
    async with async_session_factory() as session:
        yield session  # type: ignore[misc]