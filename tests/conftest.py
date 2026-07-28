"""Shared pytest fixtures for url-shortener tests."""

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.domain.entities import Link
from app.domain.ports import LinkRepository
from app.infrastructure.database import Base
from app.infrastructure.http.router import router
from app.infrastructure.models import LinkModel  # noqa: F401 — registers models
from app.infrastructure.repository import SQLAlchemyLinkRepository

# ── In-memory SQLite engine (no PostgreSQL needed in unit tests) ───────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture()
async def db_engine():  # type: ignore[no-untyped-def]
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:  # type: ignore[no-untyped-def]
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session


@pytest.fixture()
async def db_repo(db_session: AsyncSession) -> SQLAlchemyLinkRepository:
    return SQLAlchemyLinkRepository(db_session)


# ── Mock repository ────────────────────────────────────────────────────────────


class InMemoryLinkRepository(LinkRepository):
    """Thread-safe in-memory repository for unit tests."""

    def __init__(self) -> None:
        self._store: dict[str, Link] = {}

    async def get_by_short_code(self, short_code: str) -> Link | None:
        return self._store.get(short_code)

    async def save(self, link: Link) -> Link:
        self._store[link.short_code] = link
        return link

    async def increment_clicks(self, short_code: str) -> int:
        if short_code not in self._store:
            return 0
        self._store[short_code].clicks += 1
        return self._store[short_code].clicks

    async def get_stats(self, short_code: str) -> int | None:
        link = self._store.get(short_code)
        if link is None:
            return None
        return link.clicks


@pytest.fixture()
def in_memory_repo() -> InMemoryLinkRepository:
    return InMemoryLinkRepository()


# ── FastAPI test app ───────────────────────────────────────────────────────────


def build_test_app(session_factory: async_sessionmaker[AsyncSession]) -> FastAPI:
    app = FastAPI()
    app.state.session_factory = session_factory
    app.include_router(router)
    return app


@pytest.fixture()
async def app_with_db(db_engine) -> FastAPI:  # type: ignore[no-untyped-def]
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    return build_test_app(factory)


@pytest.fixture()
async def client(app_with_db: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app_with_db), base_url="http://test") as c:
        yield c


# ── Helper: seed a link directly into the DB ──────────────────────────────────


async def seed_link(
    db_session: AsyncSession,
    short_code: str,
    original_url: str = "https://example.com",
    clicks: int = 0,
) -> LinkModel:
    model = LinkModel(short_code=short_code, original_url=original_url, clicks=clicks)
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model
