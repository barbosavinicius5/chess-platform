"""Configuração de banco de dados SQLAlchemy 2.0 async."""
from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.persistence.models import Base

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./chess_platform.db")


def build_engine(url: str | None = None) -> AsyncEngine:
    db_url = url or DATABASE_URL
    connect_args: dict[str, object] = {}
    if "sqlite" in db_url:
        connect_args = {"check_same_thread": False}
    return create_async_engine(db_url, echo=False, connect_args=connect_args)


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = build_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def create_tables(engine: AsyncEngine | None = None) -> None:
    """Cria as tabelas (útil em dev e testes)."""
    eng = engine or get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables(engine: AsyncEngine | None = None) -> None:
    """Remove todas as tabelas (útil em testes)."""
    eng = engine or get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
