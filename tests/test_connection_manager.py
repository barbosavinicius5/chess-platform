"""Tests for ConnectionManager (infrastructure/websocket/connection_manager.py)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from chess.infrastructure.websocket.connection_manager import ConnectionManager


def _mock_ws() -> MagicMock:
    """Return a MagicMock that behaves like a FastAPI WebSocket."""
    ws = MagicMock()
    ws.send_text = AsyncMock()
    return ws


# ---------------------------------------------------------------------------
# connect / disconnect
# ---------------------------------------------------------------------------


def test_connect_registers_websocket() -> None:
    manager = ConnectionManager()
    ws = _mock_ws()

    manager.connect("game-1", ws)

    # The connection should be present
    assert ws in manager._connections["game-1"]


def test_disconnect_removes_websocket() -> None:
    manager = ConnectionManager()
    ws = _mock_ws()

    manager.connect("game-1", ws)
    manager.disconnect("game-1", ws)

    assert ws not in manager._connections.get("game-1", [])


def test_disconnect_unknown_websocket_does_not_raise() -> None:
    """Disconnecting a WS that was never registered must not raise."""
    manager = ConnectionManager()
    ws = _mock_ws()

    # Should not raise
    manager.disconnect("game-99", ws)


def test_connect_multiple_websockets_same_game() -> None:
    manager = ConnectionManager()
    ws1, ws2 = _mock_ws(), _mock_ws()

    manager.connect("game-1", ws1)
    manager.connect("game-1", ws2)

    assert len(manager._connections["game-1"]) == 2


# ---------------------------------------------------------------------------
# broadcast
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broadcast_sends_to_all_connections() -> None:
    manager = ConnectionManager()
    ws1, ws2 = _mock_ws(), _mock_ws()

    manager.connect("game-1", ws1)
    manager.connect("game-1", ws2)

    await manager.broadcast("game-1", "hello")

    ws1.send_text.assert_awaited_once_with("hello")
    ws2.send_text.assert_awaited_once_with("hello")


@pytest.mark.asyncio
async def test_broadcast_zero_connections_does_not_raise() -> None:
    """Broadcast with no connections must complete without exception."""
    manager = ConnectionManager()

    # Should not raise
    await manager.broadcast("game-empty", "test")


@pytest.mark.asyncio
async def test_broadcast_one_connection() -> None:
    manager = ConnectionManager()
    ws = _mock_ws()

    manager.connect("game-1", ws)
    await manager.broadcast("game-1", "msg")

    ws.send_text.assert_awaited_once_with("msg")


@pytest.mark.asyncio
async def test_broadcast_removes_stale_connections() -> None:
    """A connection that raises on send_text should be cleaned up."""
    manager = ConnectionManager()
    ws_ok = _mock_ws()
    ws_bad = _mock_ws()
    ws_bad.send_text = AsyncMock(side_effect=RuntimeError("connection lost"))

    manager.connect("game-1", ws_ok)
    manager.connect("game-1", ws_bad)

    # Should not raise even though ws_bad fails
    await manager.broadcast("game-1", "data")

    # ws_ok should still receive the message
    ws_ok.send_text.assert_awaited_once_with("data")

    # ws_bad should be removed from active connections
    assert ws_bad not in manager._connections.get("game-1", [])