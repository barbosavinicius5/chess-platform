"""SQLAlchemy async implementation of LinkRepository port."""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Link
from app.domain.ports import LinkRepository
from app.infrastructure.models import LinkModel


class SQLAlchemyLinkRepository(LinkRepository):
    """Concrete adapter: PostgreSQL + SQLAlchemy 2.0 async."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_short_code(self, short_code: str) -> Link | None:
        result = await self._session.execute(select(LinkModel).where(LinkModel.short_code == short_code))
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return Link(short_code=row.short_code, original_url=row.original_url, clicks=row.clicks)

    async def save(self, link: Link) -> Link:
        model = LinkModel(short_code=link.short_code, original_url=link.original_url, clicks=link.clicks)
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return Link(short_code=model.short_code, original_url=model.original_url, clicks=model.clicks)

    async def increment_clicks(self, short_code: str) -> int:
        """Atomic increment via UPDATE ... RETURNING (no race condition)."""
        stmt = text("UPDATE links SET clicks = clicks + 1 WHERE short_code = :code RETURNING clicks")
        result = await self._session.execute(stmt, {"code": short_code})
        await self._session.commit()
        row = result.fetchone()
        if row is None:
            return 0
        return int(row[0])

    async def get_stats(self, short_code: str) -> int | None:
        stmt = text("SELECT clicks FROM links WHERE short_code = :code")
        result = await self._session.execute(stmt, {"code": short_code})
        row = result.fetchone()
        if row is None:
            return None
        return int(row[0])
