"""Caso de uso SubmeterLance — Camada Application."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain.chess_engine import turno_atual, validar_lance
from app.infrastructure.persistence.models import GameModel

# ── Erros de domínio de aplicação ───────────────────────────────────────────

class NaoParticipanteError(Exception):
    """Jogador não é participante desta partida."""


class ForaDeTurnoError(Exception):
    """Não é a vez deste jogador."""


class LanceRecusadoError(Exception):
    """Motor de xadrez recusou o lance."""

    def __init__(self, razao: str) -> None:
        super().__init__(razao)
        self.razao = razao


# ── Porta de saída (Repositório) ─────────────────────────────────────────────

class GameRepositoryPort(Protocol):
    async def get_by_id(self, game_id: str) -> GameModel: ...

    async def save_move(
        self,
        game: GameModel,
        san: str,
        fen_resultante: str,
        jogador: str,
        novo_estado: str,
        novo_turno: str,
    ) -> object: ...


# ── Porta de saída (Unidade de Trabalho / commit) ────────────────────────────

class UnitOfWorkPort(Protocol):
    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


# ── DTO de resultado ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SubmeterLanceResult:
    game_id: str
    fen_resultante: str
    status: str
    lado: str


# ── Caso de uso ───────────────────────────────────────────────────────────────

class SubmeterLanceUseCase:
    """Orquestra a submissão de um lance em uma partida de xadrez."""

    def __init__(self, repo: GameRepositoryPort, uow: UnitOfWorkPort) -> None:
        self._repo = repo
        self._uow = uow

    async def execute(
        self,
        game_id: str,
        player_id: str,
        san: str,
    ) -> SubmeterLanceResult:
        """Executa o caso de uso de submissão de lance.

        Raises:
            NaoParticipanteError: Se o jogador não é participante da partida.
            ForaDeTurnoError: Se não é a vez do jogador.
            LanceRecusadoError: Se o motor recusou o lance.
            GameNotFoundError: Se a partida não existe (propagado do repositório).
        """
        # 1. Buscar partida
        game = await self._repo.get_by_id(game_id)

        # 2. Autorizar: é participante?
        participantes = {game.lado_jogador_branco, game.lado_jogador_preto}
        if player_id not in participantes:
            raise NaoParticipanteError("Jogador não é participante desta partida")

        # 3. Autorizar: é o jogador da vez?
        turno = game.turno  # "brancas" | "pretas"
        jogador_da_vez = (
            game.lado_jogador_branco if turno == "brancas" else game.lado_jogador_preto
        )
        if player_id != jogador_da_vez:
            raise ForaDeTurnoError("Não é a vez deste jogador")

        # 4. Validar lance no motor do Domain
        aceito, novo_fen, razao = validar_lance(game.fen_atual, san)
        if not aceito:
            raise LanceRecusadoError(razao or "Lance recusado pelo motor")

        # 5. Determinar novo estado e turno
        novo_estado = "waiting" if game.estado == "waiting" and len(game.historico_lances) == 0 else game.estado
        # Primeiro lance: waiting → in_progress
        if game.estado == "waiting":
            novo_estado = "in_progress"

        novo_turno = turno_atual(novo_fen)  # turno para o próximo lance

        # 6. Persistir atomicamente (game + move na mesma transação)
        await self._repo.save_move(
            game=game,
            san=san,
            fen_resultante=novo_fen,
            jogador=player_id,
            novo_estado=novo_estado,
            novo_turno=novo_turno,
        )
        await self._uow.commit()

        return SubmeterLanceResult(
            game_id=game_id,
            fen_resultante=novo_fen,
            status=novo_estado,
            lado=turno,  # lado que acabou de jogar
        )
