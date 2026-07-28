"""FastAPI dependency injection helpers."""

from collections.abc import AsyncGenerator
from typing import Annotated

# Session factory is set at startup via app.state
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases import CreateLinkUseCase, GetStatsUseCase, IncrementClickUseCase, ResolveLinkUseCase
from app.infrastructure.repository import SQLAlchemyLinkRepository


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with request.app.state.session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_resolve_use_case(session: SessionDep) -> ResolveLinkUseCase:
    return ResolveLinkUseCase(SQLAlchemyLinkRepository(session))


def get_create_use_case(session: SessionDep) -> CreateLinkUseCase:
    return CreateLinkUseCase(SQLAlchemyLinkRepository(session))


def get_increment_use_case(session: SessionDep) -> IncrementClickUseCase:
    return IncrementClickUseCase(SQLAlchemyLinkRepository(session))


def get_stats_use_case(session: SessionDep) -> GetStatsUseCase:
    return GetStatsUseCase(SQLAlchemyLinkRepository(session))
