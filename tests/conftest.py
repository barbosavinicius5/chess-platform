"""Shared fixtures for the test suite."""

import pytest

from chess.application.services import GameService
from chess.infrastructure.websocket.adapter import WebSocketNotifier
from chess.infrastructure.websocket.connection_manager import ConnectionManager


@pytest.fixture
def connection_manager() -> ConnectionManager:
    return ConnectionManager()


@pytest.fixture
def notifier(connection_manager: ConnectionManager) -> WebSocketNotifier:
    return WebSocketNotifier(connection_manager)


@pytest.fixture
def game_service(notifier: WebSocketNotifier) -> GameService:
    return GameService(notifier)
