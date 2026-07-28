"""Testes de unidade para o caso de uso SubmeterLance.

Usa mocks/fakes para o repositório — sem banco de dados real.
"""
from __future__ import annotations

import pytest

from app.application.use_cases.submeter_lance import (
    ForaDeTurnoError,
    LanceRecusadoError,
    NaoParticipanteError,
    SubmeterLanceUseCase,
)
from app.domain.chess_engine import FEN_INICIAL
from app.infrastructure.persistence.models import GameModel

# ── Fakes ────────────────────────────────────────────────────────────────────

PLAYER_BRANCO = "aaaaaaaa-0000-0000-0000-000000000001"
PLAYER_PRETO = "bbbbbbbb-0000-0000-0000-000000000002"
PLAYER_ESTRANHO = "cccccccc-0000-0000-0000-000000000003"
GAME_ID = "11111111-0000-0000-0000-000000000001"


def _make_game(
    estado: str = "waiting",
    fen: str = FEN_INICIAL,
    turno: str = "brancas",
    historico: list[str] | None = None,
) -> GameModel:
    game = GameModel()
    game.game_id = GAME_ID
    game.estado = estado
    game.fen_atual = fen
    game.turno = turno
    game.lado_jogador_branco = PLAYER_BRANCO
    game.lado_jogador_preto = PLAYER_PRETO
    game.historico_lances = historico or []
    game.condicao_fim = None
    return game


class FakeRepo:
    def __init__(self, game: GameModel) -> None:
        self._game = game
        self.saved_san: str | None = None
        self.saved_fen: str | None = None
        self.saved_estado: str | None = None
        self.write_count = 0

    async def get_by_id(self, game_id: str) -> GameModel:
        return self._game

    async def save_move(
        self,
        game: GameModel,
        san: str,
        fen_resultante: str,
        jogador: str,
        novo_estado: str,
        novo_turno: str,
    ) -> None:
        self.saved_san = san
        self.saved_fen = fen_resultante
        self.saved_estado = novo_estado
        self.write_count += 1


class FakeUoW:
    def __init__(self) -> None:
        self.committed = False
        self.rolledback = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolledback = True


# ── Cenário A: Aceite — jogador da vez submete lance legal ───────────────────

@pytest.mark.asyncio
async def test_cenario_a_lance_aceito() -> None:
    game = _make_game(estado="in_progress")
    repo = FakeRepo(game)
    uow = FakeUoW()
    uc = SubmeterLanceUseCase(repo=repo, uow=uow)

    result = await uc.execute(game_id=GAME_ID, player_id=PLAYER_BRANCO, san="e4")

    assert result.game_id == GAME_ID
    assert result.status == "in_progress"
    assert result.lado == "brancas"
    assert "4P3" in result.fen_resultante  # posição do peão e4
    assert uow.committed is True
    assert repo.write_count == 1


# ── Cenário B: Fora de turno ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cenario_b_fora_de_turno() -> None:
    game = _make_game(estado="in_progress", turno="brancas")
    repo = FakeRepo(game)
    uow = FakeUoW()
    uc = SubmeterLanceUseCase(repo=repo, uow=uow)

    with pytest.raises(ForaDeTurnoError):
        await uc.execute(game_id=GAME_ID, player_id=PLAYER_PRETO, san="e5")

    # Nenhuma escrita
    assert repo.write_count == 0
    assert uow.committed is False


# ── Cenário C: Não participante ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cenario_c_nao_participante() -> None:
    game = _make_game(estado="in_progress")
    repo = FakeRepo(game)
    uow = FakeUoW()
    uc = SubmeterLanceUseCase(repo=repo, uow=uow)

    with pytest.raises(NaoParticipanteError):
        await uc.execute(game_id=GAME_ID, player_id=PLAYER_ESTRANHO, san="e4")

    assert repo.write_count == 0
    assert uow.committed is False


# ── Cenário D: Lance ilegal ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cenario_d_lance_ilegal() -> None:
    game = _make_game(estado="in_progress")
    repo = FakeRepo(game)
    uow = FakeUoW()
    uc = SubmeterLanceUseCase(repo=repo, uow=uow)

    with pytest.raises(LanceRecusadoError) as exc_info:
        await uc.execute(game_id=GAME_ID, player_id=PLAYER_BRANCO, san="e9")  # posição inválida

    assert "Lance ilegal" in exc_info.value.razao
    assert repo.write_count == 0
    assert uow.committed is False


# ── Cenário E: Primeiro lance — waiting → in_progress ────────────────────────

@pytest.mark.asyncio
async def test_cenario_e_primeiro_lance_waiting_para_in_progress() -> None:
    game = _make_game(estado="waiting", turno="brancas")
    repo = FakeRepo(game)
    uow = FakeUoW()
    uc = SubmeterLanceUseCase(repo=repo, uow=uow)

    result = await uc.execute(game_id=GAME_ID, player_id=PLAYER_BRANCO, san="d4")

    assert result.status == "in_progress"
    assert repo.saved_estado == "in_progress"
    assert uow.committed is True


# ── Cenário F: Atomicidade — recusa não gera escrita ────────────────────────

@pytest.mark.asyncio
async def test_cenario_f_atomicidade_recusa_nao_escreve() -> None:
    game = _make_game(estado="in_progress")
    repo = FakeRepo(game)
    uow = FakeUoW()
    uc = SubmeterLanceUseCase(repo=repo, uow=uow)

    # Lance ilegal
    with pytest.raises(LanceRecusadoError):
        await uc.execute(game_id=GAME_ID, player_id=PLAYER_BRANCO, san="Qe9")

    assert repo.write_count == 0
    assert uow.committed is False
    # Estado inalterado
    assert game.fen_atual == FEN_INICIAL
    assert game.estado == "in_progress"


# ── Extra: razão de recusa está presente ────────────────────────────────────

@pytest.mark.asyncio
async def test_razao_recusa_presente() -> None:
    game = _make_game(estado="in_progress")
    repo = FakeRepo(game)
    uow = FakeUoW()
    uc = SubmeterLanceUseCase(repo=repo, uow=uow)

    with pytest.raises(LanceRecusadoError) as exc_info:
        await uc.execute(game_id=GAME_ID, player_id=PLAYER_BRANCO, san="Ke2")  # rei bloqueado

    assert exc_info.value.razao  # mensagem não vazia
