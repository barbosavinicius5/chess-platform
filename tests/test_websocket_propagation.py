"""Tests for WebSocket propagation — Cenários A-E da spec."""

import json
import logging
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from chess.application.services import GameService
from chess.domain.models import Game, GameStatus, Move, MoveResult
from chess.infrastructure.websocket.adapter import WebSocketNotifier
from chess.infrastructure.websocket.connection_manager import ConnectionManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_ws() -> MagicMock:
    ws = MagicMock()
    ws.send_text = AsyncMock()
    return ws


def _make_game(game_id: str = "g1") -> Game:
    game = Game(game_id=game_id, white_player_id="w", black_player_id="b")
    game.status = GameStatus.ONGOING
    return game


SAMPLE_FEN = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"


# ---------------------------------------------------------------------------
# Cenário A — Lance aceito, 2 jogadores conectados: broadcast com payload correto
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cenario_a_lance_aceito_dois_jogadores() -> None:
    """Broadcast é chamado com o payload correto quando lance é aceito."""
    manager = ConnectionManager()
    ws1, ws2 = _mock_ws(), _mock_ws()
    manager.connect("g1", ws1)
    manager.connect("g1", ws2)

    notifier = WebSocketNotifier(manager)
    await notifier.notify_move_accepted("g1", SAMPLE_FEN)

    # Both WebSockets must have received exactly one message
    ws1.send_text.assert_awaited_once()
    ws2.send_text.assert_awaited_once()

    # Inspect the payload sent to ws1
    raw: str = ws1.send_text.call_args[0][0]
    payload = json.loads(raw)

    assert payload["type"] == "lance_propagado"
    assert payload["game_id"] == "g1"
    assert payload["fen"] == SAMPLE_FEN
    assert "timestamp" in payload


# ---------------------------------------------------------------------------
# Cenário B — Lance recusado não propaga
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cenario_b_lance_recusado_nao_propaga() -> None:
    """notify_move_accepted NÃO deve ser chamado quando lance é recusado."""
    manager = ConnectionManager()
    notifier = WebSocketNotifier(manager)

    mock_notify = AsyncMock()
    notifier.notify_move_accepted = mock_notify  # type: ignore[method-assign]

    service = GameService(notifier)
    # Create a game and immediately finish it so every move is rejected
    game = service.create_game("g2", "w", "b")
    game.status = GameStatus.FINISHED  # force rejection

    move = Move(uci="e2e4", player_id="w")
    result = await service.submit_move("g2", move)

    assert result == MoveResult.REJECTED
    mock_notify.assert_not_called()


@pytest.mark.asyncio
async def test_cenario_b_recusado_sem_broadcast() -> None:
    """Nenhum broadcast deve ocorrer quando o lance é recusado."""
    manager = ConnectionManager()
    ws = _mock_ws()
    manager.connect("g2", ws)

    notifier = WebSocketNotifier(manager)
    service = GameService(notifier)

    game = service.create_game("g2", "w", "b")
    game.status = GameStatus.FINISHED  # force rejection

    move = Move(uci="", player_id="w")
    await service.submit_move("g2", move)

    ws.send_text.assert_not_called()


# ---------------------------------------------------------------------------
# Cenário C — Evento `lance_propagado` registrado no log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cenario_c_evento_lance_propagado_no_log(caplog: pytest.LogCaptureFixture) -> None:
    """Log JSON deve conter os campos obrigatórios do evento lance_propagado."""
    manager = ConnectionManager()
    notifier = WebSocketNotifier(manager)

    with caplog.at_level(logging.INFO, logger="chess.infrastructure.websocket.adapter"):
        await notifier.notify_move_accepted("g3", SAMPLE_FEN)

    # Find the lance_propagado log record
    records = [r for r in caplog.records if r.getMessage() == "lance_propagado"]
    assert records, "Nenhum log 'lance_propagado' encontrado"

    record = records[0]
    assert getattr(record, "event", None) == "lance_propagado"
    assert getattr(record, "game_id", None) == "g3"
    assert getattr(record, "fen", None) == SAMPLE_FEN
    assert hasattr(record, "latencia_propagacao_ms")
    assert hasattr(record, "timestamp")


# ---------------------------------------------------------------------------
# Cenário D — Latência de propagação < 200ms
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cenario_d_latencia_propagacao_menor_200ms(caplog: pytest.LogCaptureFixture) -> None:
    """latencia_propagacao_ms registrada deve ser < 200."""
    manager = ConnectionManager()
    # Add a few connections to simulate real fan-out
    for _ in range(2):
        manager.connect("g4", _mock_ws())

    notifier = WebSocketNotifier(manager)

    with caplog.at_level(logging.INFO, logger="chess.infrastructure.websocket.adapter"):
        start = time.monotonic()
        await notifier.notify_move_accepted("g4", SAMPLE_FEN)
        elapsed_ms = (time.monotonic() - start) * 1000

    # Wall-clock check
    assert elapsed_ms < 200, f"Propagação levou {elapsed_ms:.1f}ms (> 200ms)"

    # Logged latency check
    records = [r for r in caplog.records if r.getMessage() == "lance_propagado"]
    assert records
    latencia = getattr(records[0], "latencia_propagacao_ms", None)
    assert latencia is not None
    assert latencia < 200, f"latencia_propagacao_ms={latencia} >= 200ms"


# ---------------------------------------------------------------------------
# Cenário E — Conexão parcial: 1 jogador conectado, sem exceção
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cenario_e_um_jogador_conectado() -> None:
    """Broadcast com apenas 1 jogador conectado deve ocorrer sem exceção."""
    manager = ConnectionManager()
    ws = _mock_ws()
    manager.connect("g5", ws)

    notifier = WebSocketNotifier(manager)

    # Must not raise
    await notifier.notify_move_accepted("g5", SAMPLE_FEN)

    ws.send_text.assert_awaited_once()
    raw: str = ws.send_text.call_args[0][0]
    payload = json.loads(raw)
    assert payload["type"] == "lance_propagado"
    assert payload["game_id"] == "g5"


@pytest.mark.asyncio
async def test_cenario_e_zero_jogadores_conectados() -> None:
    """Broadcast com 0 jogadores conectados não deve lançar exceção."""
    manager = ConnectionManager()
    notifier = WebSocketNotifier(manager)

    # Must not raise
    await notifier.notify_move_accepted("g6", SAMPLE_FEN)


# ---------------------------------------------------------------------------
# Integration — GameService end-to-end (accepted path triggers broadcast)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_game_service_submit_move_accepted_triggers_notify() -> None:
    """GameService deve chamar notify_move_accepted somente em lances aceitos."""
    notifier_mock = AsyncMock(spec=WebSocketNotifier)
    service = GameService(notifier_mock)
    service.create_game("g7", "w", "b")

    move = Move(uci="e2e4", player_id="w")
    result = await service.submit_move("g7", move)

    assert result == MoveResult.ACCEPTED
    notifier_mock.notify_move_accepted.assert_awaited_once()
    call_args = notifier_mock.notify_move_accepted.call_args
    assert call_args[0][0] == "g7"  # game_id


@pytest.mark.asyncio
async def test_game_service_submit_move_game_not_found_rejected() -> None:
    """Submeter lance a game inexistente retorna REJECTED sem broadcast."""
    notifier_mock = AsyncMock(spec=WebSocketNotifier)
    service = GameService(notifier_mock)

    move = Move(uci="e2e4", player_id="w")
    result = await service.submit_move("nonexistent", move)

    assert result == MoveResult.REJECTED
    notifier_mock.notify_move_accepted.assert_not_called()
