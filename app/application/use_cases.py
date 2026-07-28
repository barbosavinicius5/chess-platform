"""Application use cases — orchestrates domain logic, no HTTP/DB deps."""

import logging

from app.domain.entities import Link
from app.domain.exceptions import LinkNotFoundError
from app.domain.ports import LinkRepository

logger = logging.getLogger(__name__)


class CreateLinkUseCase:
    """Creates a new shortened link."""

    def __init__(self, repository: LinkRepository) -> None:
        self._repository = repository

    async def execute(self, short_code: str, original_url: str) -> Link:
        link = Link(short_code=short_code, original_url=original_url, clicks=0)
        return await self._repository.save(link)


class ResolveLinkUseCase:
    """Resolves a short_code to its original URL."""

    def __init__(self, repository: LinkRepository) -> None:
        self._repository = repository

    async def execute(self, short_code: str) -> Link:
        link = await self._repository.get_by_short_code(short_code)
        if link is None:
            raise LinkNotFoundError(short_code)
        return link


class IncrementClickUseCase:
    """Atomically increments the click counter for a short_code."""

    def __init__(self, repository: LinkRepository) -> None:
        self._repository = repository

    async def execute(self, short_code: str) -> None:
        try:
            new_count = await self._repository.increment_clicks(short_code)
            logger.info(
                "click_incremented",
                extra={"short_code": short_code, "clicks": new_count},
            )
        except Exception as exc:
            logger.error(
                "click_increment_failed",
                extra={"short_code": short_code, "error": str(exc)},
                exc_info=True,
            )


class GetStatsUseCase:
    """Returns click stats for a short_code."""

    def __init__(self, repository: LinkRepository) -> None:
        self._repository = repository

    async def execute(self, short_code: str) -> int:
        clicks = await self._repository.get_stats(short_code)
        if clicks is None:
            raise LinkNotFoundError(short_code)
        return clicks
