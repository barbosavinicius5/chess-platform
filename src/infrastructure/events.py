"""Infrastructure adapter: log-based domain event emitter."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from src.domain.ports import EventEmitter

logger = logging.getLogger(__name__)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_handler)
logger.setLevel(logging.INFO)
logger.propagate = False


class LogEventEmitter(EventEmitter):
    """Emits domain events as structured JSON to stdout."""

    async def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        record = {"event": event_name, **payload}
        logger.info(json.dumps(record, ensure_ascii=False))