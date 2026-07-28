"""Unit tests for the domain layer (Game entity, GameState, GameNotFoundError)."""

from __future__ import annotations

import uuid

import pytest

from src.domain.game import INITIAL_FEN, Game, GameNotFoundError, GameState


class TestGameEntity:
    def test_create_new_returns_game_with_waiting_state(self) -> None:
        game = Game.create_new()
        assert game.estado == GameState.waiting

    def test_create_new_returns_game_with_initial_fen(self) -> None:
        game = Game.create_new()
        assert game.fen == INITIAL_FEN

    def test_create_new_returns_valid_uuid(self) -> None:
        game = Game.create_new()
        assert isinstance(game.game_id, uuid.UUID)

    def test_create_new_generates_unique_ids(self) -> None:
        g1 = Game.create_new()
        g2 = Game.create_new()
        assert g1.game_id != g2.game_id

    def test_game_repr_contains_key_fields(self) -> None:
        game = Game.create_new()
        r = repr(game)
        assert "Game(" in r
        assert str(game.game_id) in r

    def test_initial_fen_value(self) -> None:
        assert INITIAL_FEN == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


class TestGameState:
    def test_all_states_exist(self) -> None:
        assert GameState.waiting.value == "waiting"
        assert GameState.in_progress.value == "in_progress"
        assert GameState.finished.value == "finished"

    def test_state_is_string_enum(self) -> None:
        assert isinstance(GameState.waiting, str)


class TestGameNotFoundError:
    def test_error_carries_game_id(self) -> None:
        uid = uuid.uuid4()
        err = GameNotFoundError(uid)
        assert err.game_id == uid

    def test_error_message_contains_id(self) -> None:
        uid = uuid.uuid4()
        err = GameNotFoundError(uid)
        assert str(uid) in str(err)

    def test_is_exception(self) -> None:
        uid = uuid.uuid4()
        with pytest.raises(GameNotFoundError):
            raise GameNotFoundError(uid)