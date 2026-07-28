"""Dependências FastAPI — injeção de sessão de banco de dados."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.database import get_session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Fornece uma sessão async do SQLAlchemy como dependência FastAPI."""
    factory = get_session_factory()
    async with factory() as session:
        yield session
