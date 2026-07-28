"""Testes unitários de analytics e observabilidade de lances (t003).

Cobre:
- lance_aceito emitido com todas as 7 propriedades corretas
- lance_recusado emitido com as 5 propriedades corretas (ilegal e fora de turno)
- Log JSON gerado por partida/lance
- Métrica de partidas ativas reflete corretamente
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.use_cases.obter_metricas import MetricasOutput, ObterMetricasUseCase
from src.application.use_cases.submeter_lance import (
    EVENTO_LANCE_ACEITO,
    EVENTO_LANCE_RECUSADO,
    SubmeterLanceInput,
    SubmeterLanceOutput,
    SubmeterLanceUseCase,
)
from src.domain.entities.game import Game, GameStatus
from src.domain.ports.analytics_port import AnalyticsPort
from src.infrastructure.analytics.lance_analytics import LanceAnalyticsAdapter
from src.infrastructure.logging.structured_logger import JSONFormatter, get_structured_logger
from src.infrastructure.repositories.in_memory_game_repository import InMemoryGameRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _criar_partida_em_andamento(
    game_id: str = "game-001",
    player_white: str = "branco",
    player_black: str = "preto",
    fen: str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
) -> Game:
    now = datetime.now(tz=timezone.utc)
    return Game(
        id=game_id,
        player_white=player_white,
        player_black=player_black,
        status=GameStatus.IN_PROGRESS,
        fen=fen,
        created_at=now,
        updated_at=now,
    )


class _SpyAnalytics(AnalyticsPort):
    """Spy que captura todos os eventos emitidos."""

    def __init__(self) -> None:
        self.eventos: list[tuple[str, dict[str, Any]]] = []

    async def emitir_evento(self, nome: str, propriedades: dict[str, Any]) -> None:
        self.eventos.append((nome, propriedades))


# ---------------------------------------------------------------------------
# Testes: evento lance_aceito — 7 propriedades obrigatórias
# ---------------------------------------------------------------------------


class TestLanceAceito:
    """Verifica que lance_aceito é emitido com as 7 propriedades corretas."""

    @pytest.fixture()
    async def _setup(self) -> tuple[SubmeterLanceUseCase, _SpyAnalytics, InMemoryGameRepository]:
        repo = InMemoryGameRepository()
        spy = _SpyAnalytics()
        use_case = SubmeterLanceUseCase(repo=repo, analytics=spy)
        partida = _criar_partida_em_andamento()
        await repo.save(partida)
        return use_case, spy, repo

    @pytest.mark.asyncio()
    async def test_lance_aceito_emitido_ao_aceitar(
        self, _setup: tuple[SubmeterLanceUseCase, _SpyAnalytics, InMemoryGameRepository]
    ) -> None:
        use_case, spy, _ = _setup
        inp = SubmeterLanceInput(game_id="game-001", jogador="branco", san="e4")
        result = await use_case.executar(inp)

        assert result.aceito is True
        assert len(spy.eventos) == 1
        nome, props = spy.eventos[0]
        assert nome == EVENTO_LANCE_ACEITO

    @pytest.mark.asyncio()
    async def test_lance_aceito_tem_7_propriedades(
        self, _setup: tuple[SubmeterLanceUseCase, _SpyAnalytics, InMemoryGameRepository]
    ) -> None:
        use_case, spy, _ = _setup
        await use_case.executar(SubmeterLanceInput(game_id="game-001", jogador="branco", san="e4"))
        _, props = spy.eventos[0]

        assert set(props.keys()) == {
            "game_id",
            "jogador",
            "lado",
            "san",
            "fen_resultante",
            "latencia_validacao_ms",
            "timestamp",
        }

    @pytest.mark.asyncio()
    async def test_lance_aceito_valores_corretos(
        self, _setup: tuple[SubmeterLanceUseCase, _SpyAnalytics, InMemoryGameRepository]
    ) -> None:
        use_case, spy, _ = _setup
        await use_case.executar(SubmeterLanceInput(game_id="game-001", jogador="branco", san="e4"))
        _, props = spy.eventos[0]

        assert props["game_id"] == "game-001"
        assert props["jogador"] == "branco"
        assert props["lado"] == "brancas"
        assert props["san"] == "e4"
        assert isinstance(props["fen_resultante"], str)
        assert "e4" in props["fen_resultante"] or "E" in props["fen_resultante"] or len(props["fen_resultante"]) > 10
        assert isinstance(props["latencia_validacao_ms"], float)
        assert props["latencia_validacao_ms"] >= 0.0
        assert isinstance(props["timestamp"], str)
        # Valida formato ISO 8601
        datetime.fromisoformat(props["timestamp"])

    @pytest.mark.asyncio()
    async def test_lance_aceito_lado_pretas(self) -> None:
        """Verifica que lado='pretas' é emitido corretamente para o segundo jogador."""
        repo = InMemoryGameRepository()
        spy = _SpyAnalytics()
        use_case = SubmeterLanceUseCase(repo=repo, analytics=spy)

        # Partida após e4 (vez das pretas)
        fen_apos_e4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        partida = _criar_partida_em_andamento(fen=fen_apos_e4)
        await repo.save(partida)

        await use_case.executar(SubmeterLanceInput(game_id="game-001", jogador="preto", san="e5"))
        _, props = spy.eventos[0]

        assert props["lado"] == "pretas"
        assert props["jogador"] == "preto"


# ---------------------------------------------------------------------------
# Testes: evento lance_recusado — 5 propriedades obrigatórias
# ---------------------------------------------------------------------------


class TestLanceRecusado:
    """Verifica que lance_recusado é emitido com as 5 propriedades corretas."""

    @pytest.fixture()
    async def _setup_repo(self) -> InMemoryGameRepository:
        repo = InMemoryGameRepository()
        partida = _criar_partida_em_andamento()
        await repo.save(partida)
        return repo

    def _props_esperadas(self) -> set[str]:
        return {"game_id", "jogador", "san", "razao", "timestamp"}

    @pytest.mark.asyncio()
    async def test_lance_recusado_por_ilegalidade(self, _setup_repo: InMemoryGameRepository) -> None:
        """Lance ilegal emite lance_recusado com 5 propriedades."""
        spy = _SpyAnalytics()
        use_case = SubmeterLanceUseCase(repo=_setup_repo, analytics=spy)

        result = await use_case.executar(SubmeterLanceInput(game_id="game-001", jogador="branco", san="e9"))

        assert result.aceito is False
        assert len(spy.eventos) == 1
        nome, props = spy.eventos[0]
        assert nome == EVENTO_LANCE_RECUSADO
        assert set(props.keys()) == self._props_esperadas()

    @pytest.mark.asyncio()
    async def test_lance_recusado_ilegal_valores(self, _setup_repo: InMemoryGameRepository) -> None:
        spy = _SpyAnalytics()
        use_case = SubmeterLanceUseCase(repo=_setup_repo, analytics=spy)
        await use_case.executar(SubmeterLanceInput(game_id="game-001", jogador="branco", san="Ke8"))

        _, props = spy.eventos[0]
        assert props["game_id"] == "game-001"
        assert props["jogador"] == "branco"
        assert props["san"] == "Ke8"
        assert props["razao"] == "lance_ilegal"
        assert isinstance(props["timestamp"], str)
        datetime.fromisoformat(props["timestamp"])

    @pytest.mark.asyncio()
    async def test_lance_recusado_fora_de_turno(self, _setup_repo: InMemoryGameRepository) -> None:
        """Jogador fora de turno emite lance_recusado com razão='fora_de_turno'."""
        spy = _SpyAnalytics()
        use_case = SubmeterLanceUseCase(repo=_setup_repo, analytics=spy)

        # É vez das brancas, então o preto está fora de turno
        result = await use_case.executar(SubmeterLanceInput(game_id="game-001", jogador="preto", san="e5"))

        assert result.aceito is False
        nome, props = spy.eventos[0]
        assert nome == EVENTO_LANCE_RECUSADO
        assert props["razao"] == "fora_de_turno"
        assert set(props.keys()) == self._props_esperadas()

    @pytest.mark.asyncio()
    async def test_lance_recusado_jogador_nao_participa(self, _setup_repo: InMemoryGameRepository) -> None:
        """Jogador que não participa emite lance_recusado."""
        spy = _SpyAnalytics()
        use_case = SubmeterLanceUseCase(repo=_setup_repo, analytics=spy)

        result = await use_case.executar(
            SubmeterLanceInput(game_id="game-001", jogador="intruso", san="e4")
        )

        assert result.aceito is False
        nome, props = spy.eventos[0]
        assert nome == EVENTO_LANCE_RECUSADO
        assert props["razao"] == "jogador_nao_participa"
        assert set(props.keys()) == self._props_esperadas()

    @pytest.mark.asyncio()
    async def test_lance_recusado_partida_nao_encontrada(self) -> None:
        """Partida inexistente emite lance_recusado."""
        repo = InMemoryGameRepository()
        spy = _SpyAnalytics()
        use_case = SubmeterLanceUseCase(repo=repo, analytics=spy)

        result = await use_case.executar(
            SubmeterLanceInput(game_id="inexistente", jogador="branco", san="e4")
        )

        assert result.aceito is False
        nome, props = spy.eventos[0]
        assert nome == EVENTO_LANCE_RECUSADO
        assert props["razao"] == "partida_nao_encontrada"

    @pytest.mark.asyncio()
    async def test_lance_recusado_partida_nao_em_andamento(self) -> None:
        """Partida com status diferente de in_progress emite lance_recusado."""
        repo = InMemoryGameRepository()
        now = datetime.now(tz=timezone.utc)
        partida = Game(
            id="game-002",
            player_white="branco",
            player_black="preto",
            status=GameStatus.WAITING,
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            created_at=now,
            updated_at=now,
        )
        await repo.save(partida)
        spy = _SpyAnalytics()
        use_case = SubmeterLanceUseCase(repo=repo, analytics=spy)

        result = await use_case.executar(
            SubmeterLanceInput(game_id="game-002", jogador="branco", san="e4")
        )

        assert result.aceito is False
        _, props = spy.eventos[0]
        assert props["razao"] == "partida_nao_em_andamento"


# ---------------------------------------------------------------------------
# Testes: Log JSON estruturado
# ---------------------------------------------------------------------------


class TestLogEstruturadoJSON:
    """Verifica que o log JSON estruturado é gerado por partida/lance."""

    @pytest.mark.asyncio()
    async def test_log_gerado_ao_aceitar_lance(self) -> None:
        """Verifica que um log JSON é emitido quando um lance é aceito."""
        repo = InMemoryGameRepository()
        spy = _SpyAnalytics()
        use_case = SubmeterLanceUseCase(repo=repo, analytics=spy)
        partida = _criar_partida_em_andamento()
        await repo.save(partida)

        records: list[logging.LogRecord] = []

        class _CapturingHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        handler = _CapturingHandler()
        logger = get_structured_logger("chess.use_case.submeter_lance")
        logger.addHandler(handler)

        try:
            await use_case.executar(SubmeterLanceInput(game_id="game-001", jogador="branco", san="e4"))
        finally:
            logger.removeHandler(handler)

        assert len(records) >= 1
        record = records[0]
        # Verifica que o registro tem os campos de contexto necessários
        assert hasattr(record, "game_id")
        assert record.game_id == "game-001"  # type: ignore[attr-defined]
        assert hasattr(record, "jogador")
        assert hasattr(record, "san")
        assert hasattr(record, "resultado")

    @pytest.mark.asyncio()
    async def test_log_gerado_ao_recusar_lance(self) -> None:
        """Verifica que um log JSON é emitido quando um lance é recusado."""
        repo = InMemoryGameRepository()
        spy = _SpyAnalytics()
        use_case = SubmeterLanceUseCase(repo=repo, analytics=spy)
        partida = _criar_partida_em_andamento()
        await repo.save(partida)

        records: list[logging.LogRecord] = []

        class _CapturingHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        handler = _CapturingHandler()
        logger = get_structured_logger("chess.use_case.submeter_lance")
        logger.addHandler(handler)

        try:
            await use_case.executar(SubmeterLanceInput(game_id="game-001", jogador="preto", san="e5"))
        finally:
            logger.removeHandler(handler)

        assert len(records) >= 1
        record = records[0]
        assert record.game_id == "game-001"  # type: ignore[attr-defined]
        assert record.resultado == "recusado"  # type: ignore[attr-defined]

    def test_json_formatter_produz_json_valido(self) -> None:
        """Verifica que o JSONFormatter produz JSON parseável."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="teste",
            args=(),
            exc_info=None,
        )
        record.game_id = "game-999"  # type: ignore[attr-defined]
        record.jogador = "branco"  # type: ignore[attr-defined]

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["message"] == "teste"
        assert parsed["level"] == "INFO"
        assert parsed["game_id"] == "game-999"
        assert parsed["jogador"] == "branco"
        assert "timestamp" in parsed

    def test_json_formatter_campos_obrigatorios(self) -> None:
        """Verifica que o JSON sempre contém os campos obrigatórios."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="chess.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="mensagem de teste",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)

        assert "timestamp" in parsed
        assert "level" in parsed
        assert "logger" in parsed
        assert "message" in parsed

    @pytest.mark.asyncio()
    async def test_analytics_adapter_emite_log_json(self) -> None:
        """Verifica que o LanceAnalyticsAdapter emite log JSON parseável no stdout."""
        registros: list[str] = []

        class _HandlerCaptura(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                registros.append(JSONFormatter().format(record))

        handler = _HandlerCaptura()
        logger = logging.getLogger("chess.analytics.lances")
        logger.addHandler(handler)

        try:
            adapter = LanceAnalyticsAdapter()
            await adapter.emitir_evento("lance_aceito", {"game_id": "g1", "jogador": "branco"})
        finally:
            logger.removeHandler(handler)

        assert len(registros) >= 1
        parsed = json.loads(registros[0])
        assert parsed["evento"] == "lance_aceito"
        assert parsed["game_id"] == "g1"


# ---------------------------------------------------------------------------
# Testes: Métrica de partidas ativas
# ---------------------------------------------------------------------------


class TestMetricaPartidasAtivas:
    """Verifica que a métrica de partidas ativas reflete corretamente."""

    @pytest.mark.asyncio()
    async def test_zero_partidas_ativas_inicial(self) -> None:
        repo = InMemoryGameRepository()
        use_case = ObterMetricasUseCase(repo=repo)
        result = await use_case.executar()
        assert result.partidas_ativas == 0

    @pytest.mark.asyncio()
    async def test_uma_partida_ativa(self) -> None:
        repo = InMemoryGameRepository()
        partida = _criar_partida_em_andamento()
        await repo.save(partida)

        use_case = ObterMetricasUseCase(repo=repo)
        result = await use_case.executar()
        assert result.partidas_ativas == 1

    @pytest.mark.asyncio()
    async def test_apenas_in_progress_conta_como_ativa(self) -> None:
        """Apenas partidas com status in_progress são contadas."""
        repo = InMemoryGameRepository()
        now = datetime.now(tz=timezone.utc)

        # Partida em andamento
        await repo.save(_criar_partida_em_andamento(game_id="g1"))

        # Partida aguardando
        waiting = Game(
            id="g2",
            player_white="a",
            player_black="b",
            status=GameStatus.WAITING,
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            created_at=now,
            updated_at=now,
        )
        await repo.save(waiting)

        # Partida finalizada
        finished = Game(
            id="g3",
            player_white="c",
            player_black="d",
            status=GameStatus.FINISHED,
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            created_at=now,
            updated_at=now,
        )
        await repo.save(finished)

        use_case = ObterMetricasUseCase(repo=repo)
        result = await use_case.executar()
        assert result.partidas_ativas == 1

    @pytest.mark.asyncio()
    async def test_multiplas_partidas_ativas(self) -> None:
        """Múltiplas partidas in_progress são todas contadas."""
        repo = InMemoryGameRepository()
        for i in range(5):
            await repo.save(_criar_partida_em_andamento(game_id=f"game-{i:03d}"))

        use_case = ObterMetricasUseCase(repo=repo)
        result = await use_case.executar()
        assert result.partidas_ativas == 5

    @pytest.mark.asyncio()
    async def test_metrica_atualiza_apos_partida_finalizar(self) -> None:
        """Métrica diminui após uma partida terminar."""
        repo = InMemoryGameRepository()

        # Adiciona 2 partidas ativas
        await repo.save(_criar_partida_em_andamento(game_id="g1"))
        await repo.save(_criar_partida_em_andamento(game_id="g2"))

        use_case = ObterMetricasUseCase(repo=repo)
        result_antes = await use_case.executar()
        assert result_antes.partidas_ativas == 2

        # Finaliza uma partida
        game = await repo.get_by_id("g1")
        assert game is not None
        game.status = GameStatus.FINISHED
        await repo.save(game)

        result_depois = await use_case.executar()
        assert result_depois.partidas_ativas == 1

    @pytest.mark.asyncio()
    async def test_metrica_output_tem_campo_correto(self) -> None:
        """Verifica estrutura do MetricasOutput."""
        repo = InMemoryGameRepository()
        use_case = ObterMetricasUseCase(repo=repo)
        result = await use_case.executar()
        assert isinstance(result, MetricasOutput)
        assert hasattr(result, "partidas_ativas")
        assert isinstance(result.partidas_ativas, int)


# ---------------------------------------------------------------------------
# Testes: LanceAnalyticsAdapter
# ---------------------------------------------------------------------------


class TestLanceAnalyticsAdapter:
    """Testes do adaptador de analytics."""

    @pytest.mark.asyncio()
    async def test_adapter_emite_evento_com_nome_correto(self) -> None:
        registros: list[str] = []

        class _HandlerCaptura(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                registros.append(JSONFormatter().format(record))

        handler = _HandlerCaptura()
        logger = logging.getLogger("chess.analytics.lances")
        logger.addHandler(handler)

        try:
            adapter = LanceAnalyticsAdapter()
            await adapter.emitir_evento("lance_recusado", {"game_id": "g1", "razao": "fora_de_turno"})
        finally:
            logger.removeHandler(handler)

        assert registros
        parsed = json.loads(registros[0])
        assert parsed["evento"] == "lance_recusado"

    @pytest.mark.asyncio()
    async def test_adapter_preserva_todas_propriedades(self) -> None:
        """Todas as propriedades do evento são preservadas no log JSON."""
        registros: list[str] = []

        class _HandlerCaptura(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                registros.append(JSONFormatter().format(record))

        handler = _HandlerCaptura()
        logger = logging.getLogger("chess.analytics.lances")
        logger.addHandler(handler)

        propriedades = {
            "game_id": "g-abc",
            "jogador": "magnus",
            "lado": "brancas",
            "san": "Nf3",
            "fen_resultante": "rnbqkb1r/pppppppp/5n2/8/8/5N2/PPPPPPPP/RNBQKB1R w KQkq - 2 2",
            "latencia_validacao_ms": 12.5,
            "timestamp": "2026-01-01T00:00:00+00:00",
        }
        try:
            adapter = LanceAnalyticsAdapter()
            await adapter.emitir_evento("lance_aceito", propriedades)
        finally:
            logger.removeHandler(handler)

        assert registros
        parsed = json.loads(registros[0])
        for key, value in propriedades.items():
            assert parsed[key] == value


# ---------------------------------------------------------------------------
# Testes: Domínio (Game entity)
# ---------------------------------------------------------------------------


class TestGameEntity:
    """Testes da entidade Game."""

    def test_lado_do_jogador_brancas(self) -> None:
        now = datetime.now(tz=timezone.utc)
        game = Game(
            id="g1",
            player_white="w",
            player_black="b",
            status=GameStatus.IN_PROGRESS,
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            created_at=now,
            updated_at=now,
        )
        assert game.lado_do_jogador("w") == "brancas"
        assert game.lado_do_jogador("b") == "pretas"
        assert game.lado_do_jogador("outro") is None

    def test_is_vez_do_jogador(self) -> None:
        now = datetime.now(tz=timezone.utc)
        game = Game(
            id="g1",
            player_white="w",
            player_black="b",
            status=GameStatus.IN_PROGRESS,
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            created_at=now,
            updated_at=now,
        )
        assert game.is_vez_do_jogador("w") is True
        assert game.is_vez_do_jogador("b") is False

    def test_game_create(self) -> None:
        game = Game.create("w", "b")
        assert game.status == GameStatus.WAITING
        assert game.player_white == "w"
        assert game.player_black == "b"
        assert len(game.id) > 0