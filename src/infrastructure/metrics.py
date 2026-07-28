"""Infrastructure adapter: in-memory metrics counter."""

from __future__ import annotations

import asyncio
from collections import defaultdict

from src.domain.ports import MetricsCounter


class InMemoryMetricsCounter(MetricsCounter):
    """Thread-safe in-memory counter backed by an asyncio.Lock."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def increment(self, metric_name: str) -> None:
        async with self._lock:
            self._counters[metric_name] += 1

    def get(self, metric_name: str) -> int:
        """Helper for tests / observability — not part of the port."""
        return self._counters[metric_name]