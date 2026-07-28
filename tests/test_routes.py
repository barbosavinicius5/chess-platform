"""Tests for FastAPI REST routes (infrastructure/api/routes.py)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from chess.application.services import GameService
from chess.infrastructure.api.routes import router
from chess.infrastructure.websocket.adapter import WebSocketNotifier
from chess.infrastructure.websocket.connection_manager import ConnectionManager


@pytest.fixture
def app() -> FastAPI:
    """Create a fresh FastAPI app with isolated game_service for each test."""
    fresh_manager = ConnectionManager()
    fresh_notifier = WebSocketNotifier(fresh_manager)
    fresh_service = GameService(fresh_notifier)

    from chess.infrastructure.api import routes as _routes

    _routes.connection_manager = fresh_manager
    _routes.game_service = fresh_service

    _app = FastAPI()
    _app.include_router(router)
    return _app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_create_game_returns_201(client: TestClient) -> None:
    resp = client.post(
        "/games",
        json={"game_id": "g-route-1", "white_player_id": "w", "black_player_id": "b"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["game_id"] == "g-route-1"
    assert "fen" in body


def test_submit_move_accepted(client: TestClient) -> None:
    client.post(
        "/games",
        json={"game_id": "g-route-2", "white_player_id": "w", "black_player_id": "b"},
    )
    resp = client.post(
        "/games/g-route-2/moves",
        json={"uci": "e2e4", "player_id": "w"},
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == "accepted"


def test_submit_move_rejected_game_not_found(client: TestClient) -> None:
    resp = client.post(
        "/games/nonexistent/moves",
        json={"uci": "e2e4", "player_id": "w"},
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == "rejected"


def test_websocket_connect_and_receive() -> None:
    """WebSocket connects, receives a broadcast message, then disconnects."""
    fresh_manager = ConnectionManager()
    fresh_notifier = WebSocketNotifier(fresh_manager)
    fresh_service = GameService(fresh_notifier)

    from chess.infrastructure.api import routes as _routes

    _routes.connection_manager = fresh_manager
    _routes.game_service = fresh_service

    _app = FastAPI()
    _app.include_router(router)

    fresh_service.create_game("g-ws", "w", "b")

    with TestClient(_app) as tc:
        with tc.websocket_connect("/games/g-ws/live") as ws:
            # Trigger a move so the broadcast is sent to the WS client
            tc.post(
                "/games/g-ws/moves",
                json={"uci": "e2e4", "player_id": "w"},
            )
            data = ws.receive_json()
            assert data["type"] == "lance_propagado"
            assert data["game_id"] == "g-ws"
            assert "fen" in data
            assert "timestamp" in data