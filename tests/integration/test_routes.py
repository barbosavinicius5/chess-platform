"""Integration tests for HTTP routes — uses an in-memory repository (no real DB)."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app
from src.domain.game import INITIAL_FEN, Game
from src.domain.ports import EventEmitter, GameRepository, MetricsCounter
from src.infrastructure.http.routes import get_event_emitter, get_metrics_counter, get_repository

# ---------------------------------------------------------------------------
# In-memory stubs (same as unit tests — duplicated intentionally for isolation)
# ---------------------------------------------------------------------------


class _InMemoryRepo(GameRepository):
    def __init__(self) -> None:
        self._store: dict[uuid.UUID, Game] = {}

    async def save(self, game: Game) -> None:
        self._store[game.game_id] = game

    async def get_by_id(self, game_id: uuid.UUID) -> Game | None:
        return self._store.get(game_id)


class _InMemoryEmitter(EventEmitter):
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        self.events.append((event_name, payload))


class _InMemoryMetrics(MetricsCounter):
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}

    async def increment(self, metric_name: str) -> None:
        self.counters[metric_name] = self.counters.get(metric_name, 0) + 1


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo() -> _InMemoryRepo:
    return _InMemoryRepo()


@pytest.fixture()
def emitter() -> _InMemoryEmitter:
    return _InMemoryEmitter()


@pytest.fixture()
def metrics() -> _InMemoryMetrics:
    return _InMemoryMetrics()


@pytest.fixture()
def client(repo: _InMemoryRepo, emitter: _InMemoryEmitter, metrics: _InMemoryMetrics) -> TestClient:
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_event_emitter] = lambda: emitter
    app.dependency_overrides[get_metrics_counter] = lambda: metrics
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Cenário A: criação bem-sucedida
# ---------------------------------------------------------------------------


class TestPostGames:
    def test_cenario_a_returns_201(self, client: TestClient) -> None:
        response = client.post("/games")
        assert response.status_code == 201

    def test_cenario_a_returns_waiting_state(self, client: TestClient) -> None:
        response = client.post("/games")
        assert response.json()["estado"] == "waiting"

    def test_cenario_a_returns_correct_fen(self, client: TestClient) -> None:
        response = client.post("/games")
        assert response.json()["fen"] == INITIAL_FEN

    def test_cenario_a_returns_valid_game_id(self, client: TestClient) -> None:
        response = client.post("/games")
        body = response.json()
        assert "game_id" in body
        # Must be a valid UUID
        uuid.UUID(body["game_id"])

    def test_cenario_a_event_emitted(self, client: TestClient, emitter: _InMemoryEmitter) -> None:
        client.post("/games")
        assert len(emitter.events) == 1
        assert emitter.events[0][0] == "partida_criada"

    def test_cenario_a_metric_incremented(self, client: TestClient, metrics: _InMemoryMetrics) -> None:
        client.post("/games")
        assert metrics.counters.get("partidas_ativas") == 1


# ---------------------------------------------------------------------------
# Cenário B: consulta idempotente
# ---------------------------------------------------------------------------


class TestGetGameByIdFound:
    def test_cenario_b_returns_200(self, client: TestClient, repo: _InMemoryRepo) -> None:
        post_resp = client.post("/games")
        game_id = post_resp.json()["game_id"]
        get_resp = client.get(f"/games/{game_id}")
        assert get_resp.status_code == 200

    def test_cenario_b_returns_same_state(self, client: TestClient) -> None:
        post_resp = client.post("/games")
        body = post_resp.json()
        game_id = body["game_id"]
        get_resp = client.get(f"/games/{game_id}")
        assert get_resp.json()["estado"] == body["estado"]

    def test_cenario_b_returns_same_fen(self, client: TestClient) -> None:
        post_resp = client.post("/games")
        body = post_resp.json()
        game_id = body["game_id"]
        get_resp = client.get(f"/games/{game_id}")
        assert get_resp.json()["fen"] == body["fen"]

    def test_cenario_b_idempotent_multiple_gets(self, client: TestClient) -> None:
        post_resp = client.post("/games")
        game_id = post_resp.json()["game_id"]
        resp1 = client.get(f"/games/{game_id}")
        resp2 = client.get(f"/games/{game_id}")
        assert resp1.json() == resp2.json()


# ---------------------------------------------------------------------------
# Cenário C: game_id inexistente → 404
# ---------------------------------------------------------------------------


class TestGetGameByIdNotFound:
    def test_cenario_c_returns_404(self, client: TestClient) -> None:
        response = client.get(f"/games/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_cenario_c_returns_error_message(self, client: TestClient) -> None:
        response = client.get(f"/games/{uuid.uuid4()}")
        # FastAPI wraps HTTPException detail under "detail"
        body = response.json()
        # We raise with detail={"error": "Partida não encontrada"}
        assert body["detail"]["error"] == "Partida não encontrada"


# ---------------------------------------------------------------------------
# Cenário D: falha no repositório → 5xx, sem evento, sem métrica
# ---------------------------------------------------------------------------


class TestCreateGameRepoFailure:
    @pytest.fixture()
    def failing_client(self, emitter: _InMemoryEmitter, metrics: _InMemoryMetrics) -> TestClient:
        failing_repo: GameRepository = MagicMock(spec=GameRepository)
        failing_repo.save = AsyncMock(side_effect=RuntimeError("db exploded"))  # type: ignore[method-assign]
        app.dependency_overrides[get_repository] = lambda: failing_repo
        app.dependency_overrides[get_event_emitter] = lambda: emitter
        app.dependency_overrides[get_metrics_counter] = lambda: metrics
        yield TestClient(app, raise_server_exceptions=False)
        app.dependency_overrides.clear()

    def test_cenario_d_returns_5xx(
        self, failing_client: TestClient
    ) -> None:
        response = failing_client.post("/games")
        assert response.status_code >= 500

    def test_cenario_d_no_event_emitted(
        self, failing_client: TestClient, emitter: _InMemoryEmitter
    ) -> None:
        failing_client.post("/games")
        assert emitter.events == []

    def test_cenario_d_no_metric_incremented(
        self, failing_client: TestClient, metrics: _InMemoryMetrics
    ) -> None:
        failing_client.post("/games")
        assert metrics.counters.get("partidas_ativas", 0) == 0