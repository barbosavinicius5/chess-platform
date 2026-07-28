"""Unit tests for infrastructure adapters (events, metrics, models, repository)."""

from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.game import INITIAL_FEN, Game, GameState
from src.infrastructure.events import LogEventEmitter
from src.infrastructure.metrics import InMemoryMetricsCounter

# ---------------------------------------------------------------------------
# LogEventEmitter
# ---------------------------------------------------------------------------


class TestLogEventEmitter:
    async def test_emit_logs_json_with_event_name(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging

        emitter = LogEventEmitter()
        payload: dict[str, Any] = {"game_id": "abc-123", "estado": "waiting"}
        with caplog.at_level(logging.INFO, logger="src.infrastructure.events"):
            await emitter.emit("partida_criada", payload)
        assert len(caplog.records) == 1
        record_json = json.loads(caplog.records[0].message)
        assert record_json["event"] == "partida_criada"
        assert record_json["game_id"] == "abc-123"
        assert record_json["estado"] == "waiting"

    async def test_emit_includes_all_payload_keys(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging

        emitter = LogEventEmitter()
        payload = {"a": 1, "b": "two", "c": True}
        with caplog.at_level(logging.INFO, logger="src.infrastructure.events"):
            await emitter.emit("test_event", payload)
        record_json = json.loads(caplog.records[0].message)
        assert record_json["a"] == 1
        assert record_json["b"] == "two"
        assert record_json["c"] is True

    async def test_emit_event_name_in_record(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging

        emitter = LogEventEmitter()
        with caplog.at_level(logging.INFO, logger="src.infrastructure.events"):
            await emitter.emit("my_event", {})
        record_json = json.loads(caplog.records[0].message)
        assert record_json["event"] == "my_event"


# ---------------------------------------------------------------------------
# InMemoryMetricsCounter
# ---------------------------------------------------------------------------


class TestInMemoryMetricsCounter:
    async def test_increment_increases_counter_by_one(self) -> None:
        counter = InMemoryMetricsCounter()
        await counter.increment("partidas_ativas")
        assert counter.get("partidas_ativas") == 1

    async def test_increment_multiple_times(self) -> None:
        counter = InMemoryMetricsCounter()
        await counter.increment("partidas_ativas")
        await counter.increment("partidas_ativas")
        await counter.increment("partidas_ativas")
        assert counter.get("partidas_ativas") == 3

    async def test_independent_counters(self) -> None:
        counter = InMemoryMetricsCounter()
        await counter.increment("metric_a")
        await counter.increment("metric_b")
        await counter.increment("metric_b")
        assert counter.get("metric_a") == 1
        assert counter.get("metric_b") == 2

    def test_get_unknown_metric_returns_zero(self) -> None:
        counter = InMemoryMetricsCounter()
        assert counter.get("non_existent") == 0

    async def test_starts_at_zero(self) -> None:
        counter = InMemoryMetricsCounter()
        assert counter.get("partidas_ativas") == 0


# ---------------------------------------------------------------------------
# AsyncGameRepository (mocked SQLAlchemy session)
# ---------------------------------------------------------------------------


class TestAsyncGameRepository:
    def _make_repo(self) -> tuple[Any, Any]:
        """Return (repo, mock_session)."""
        from src.infrastructure.repositories import AsyncGameRepository

        session = MagicMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.execute = AsyncMock()
        repo = AsyncGameRepository(session)
        return repo, session

    async def test_save_adds_model_and_commits(self) -> None:
        repo, session = self._make_repo()
        game = Game.create_new()
        await repo.save(game)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()

    async def test_save_model_has_correct_fields(self) -> None:
        repo, session = self._make_repo()
        game = Game.create_new()
        await repo.save(game)
        model = session.add.call_args[0][0]
        assert model.game_id == game.game_id
        assert model.estado == "waiting"
        assert model.fen == INITIAL_FEN

    async def test_get_by_id_returns_none_when_not_found(self) -> None:
        repo, session = self._make_repo()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock
        result = await repo.get_by_id(uuid.uuid4())
        assert result is None

    async def test_get_by_id_returns_game_when_found(self) -> None:
        repo, session = self._make_repo()
        game_id = uuid.uuid4()

        model = MagicMock()
        model.game_id = game_id
        model.estado = "waiting"
        model.fen = INITIAL_FEN

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = model
        session.execute.return_value = result_mock

        game = await repo.get_by_id(game_id)
        assert game is not None
        assert game.game_id == game_id
        assert game.estado == GameState.waiting
        assert game.fen == INITIAL_FEN


# ---------------------------------------------------------------------------
# GameModel
# ---------------------------------------------------------------------------


class TestGameModel:
    def test_model_has_correct_tablename(self) -> None:
        from src.infrastructure.models import GameModel

        assert GameModel.__tablename__ == "games"

    def test_model_columns_exist(self) -> None:
        from src.infrastructure.models import GameModel

        columns = {col.name for col in GameModel.__table__.columns}
        assert "game_id" in columns
        assert "estado" in columns
        assert "fen" in columns