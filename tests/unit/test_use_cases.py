"""Unit tests for application use cases using mock adapters."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.create_game import CreateGameUseCase
from src.application.get_game import GetGameUseCase
from src.domain.game import INITIAL_FEN, Game, GameNotFoundError, GameState
from src.domain.ports import EventEmitter, GameRepository, MetricsCounter

# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------


class InMemoryGameRepository(GameRepository):
    """In-memory stub implementing the GameRepository port."""

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, Game] = {}

    async def save(self, game: Game) -> None:
        self._store[game.game_id] = game

    async def get_by_id(self, game_id: uuid.UUID) -> Game | None:
        return self._store.get(game_id)


class InMemoryEventEmitter(EventEmitter):
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        self.events.append((event_name, payload))


class InMemoryMetricsCounter(MetricsCounter):
    def __init__(self) -> None:
        self.counters: dict[str, int] = {}

    async def increment(self, metric_name: str) -> None:
        self.counters[metric_name] = self.counters.get(metric_name, 0) + 1


# ---------------------------------------------------------------------------
# CreateGameUseCase
# ---------------------------------------------------------------------------


class TestCreateGameUseCase:
    @pytest.fixture
    def deps(self) -> tuple[InMemoryGameRepository, InMemoryEventEmitter, InMemoryMetricsCounter]:
        return InMemoryGameRepository(), InMemoryEventEmitter(), InMemoryMetricsCounter()

    async def test_returns_game_with_waiting_state(
        self, deps: tuple[InMemoryGameRepository, InMemoryEventEmitter, InMemoryMetricsCounter]
    ) -> None:
        repo, emitter, metrics = deps
        uc = CreateGameUseCase(repo, emitter, metrics)
        game = await uc.execute()
        assert game.estado == GameState.waiting

    async def test_returns_game_with_initial_fen(
        self, deps: tuple[InMemoryGameRepository, InMemoryEventEmitter, InMemoryMetricsCounter]
    ) -> None:
        repo, emitter, metrics = deps
        uc = CreateGameUseCase(repo, emitter, metrics)
        game = await uc.execute()
        assert game.fen == INITIAL_FEN

    async def test_persists_game_in_repository(
        self, deps: tuple[InMemoryGameRepository, InMemoryEventEmitter, InMemoryMetricsCounter]
    ) -> None:
        repo, emitter, metrics = deps
        uc = CreateGameUseCase(repo, emitter, metrics)
        game = await uc.execute()
        stored = await repo.get_by_id(game.game_id)
        assert stored is not None
        assert stored.game_id == game.game_id

    async def test_emits_partida_criada_event(
        self, deps: tuple[InMemoryGameRepository, InMemoryEventEmitter, InMemoryMetricsCounter]
    ) -> None:
        repo, emitter, metrics = deps
        uc = CreateGameUseCase(repo, emitter, metrics)
        game = await uc.execute()
        assert len(emitter.events) == 1
        name, payload = emitter.events[0]
        assert name == "partida_criada"
        assert payload["game_id"] == str(game.game_id)
        assert payload["estado"] == "waiting"
        assert payload["fen_inicial"] == INITIAL_FEN
        assert "timestamp" in payload

    async def test_increments_partidas_ativas_metric(
        self, deps: tuple[InMemoryGameRepository, InMemoryEventEmitter, InMemoryMetricsCounter]
    ) -> None:
        repo, emitter, metrics = deps
        uc = CreateGameUseCase(repo, emitter, metrics)
        await uc.execute()
        assert metrics.counters.get("partidas_ativas") == 1

    async def test_no_event_emitted_when_repo_raises(
        self, deps: tuple[InMemoryGameRepository, InMemoryEventEmitter, InMemoryMetricsCounter]
    ) -> None:
        """Cenário D: repository failure → no side-effects."""
        _, emitter, metrics = deps
        failing_repo: GameRepository = MagicMock(spec=GameRepository)
        failing_repo.save = AsyncMock(side_effect=RuntimeError("db error"))  # type: ignore[method-assign]
        uc = CreateGameUseCase(failing_repo, emitter, metrics)
        with pytest.raises(RuntimeError):
            await uc.execute()
        assert emitter.events == []
        assert metrics.counters.get("partidas_ativas", 0) == 0

    async def test_no_metric_incremented_when_repo_raises(
        self, deps: tuple[InMemoryGameRepository, InMemoryEventEmitter, InMemoryMetricsCounter]
    ) -> None:
        _, emitter, metrics = deps
        failing_repo: GameRepository = MagicMock(spec=GameRepository)
        failing_repo.save = AsyncMock(side_effect=RuntimeError("db error"))  # type: ignore[method-assign]
        uc = CreateGameUseCase(failing_repo, emitter, metrics)
        with pytest.raises(RuntimeError):
            await uc.execute()
        assert metrics.counters.get("partidas_ativas", 0) == 0


# ---------------------------------------------------------------------------
# GetGameUseCase
# ---------------------------------------------------------------------------


class TestGetGameUseCase:
    async def test_returns_existing_game(self) -> None:
        repo = InMemoryGameRepository()
        game = Game.create_new()
        await repo.save(game)
        uc = GetGameUseCase(repo)
        result = await uc.execute(game.game_id)
        assert result.game_id == game.game_id
        assert result.estado == GameState.waiting
        assert result.fen == INITIAL_FEN

    async def test_raises_game_not_found_error_for_unknown_id(self) -> None:
        repo = InMemoryGameRepository()
        uc = GetGameUseCase(repo)
        with pytest.raises(GameNotFoundError) as exc_info:
            await uc.execute(uuid.uuid4())
        assert isinstance(exc_info.value, GameNotFoundError)