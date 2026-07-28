"""Repositório de partidas — Camada Infrastructure/Persistence."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models import GameModel, MoveModel


class GameNotFoundError(Exception):
    pass


class GameRepository:
    """Acesso a dados de partidas usando SQLAlchemy 2.0 async."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, game_id: str) -> GameModel:
        """Busca partida por ID; levanta GameNotFoundError se inexistente."""
        result = await self._session.execute(select(GameModel).where(GameModel.game_id == game_id))
        game = result.scalar_one_or_none()
        if game is None:
            raise GameNotFoundError(f"Partida {game_id!r} não encontrada")
        return game

    async def save_move(
        self,
        game: GameModel,
        san: str,
        fen_resultante: str,
        jogador: str,
        novo_estado: str,
        novo_turno: str,
    ) -> MoveModel:
        """Persiste atomicamente o novo estado da partida + registro de lance."""
        numero_lance = len(game.historico_lances) + 1

        # Atualiza partida
        game.fen_atual = fen_resultante
        game.turno = novo_turno
        game.estado = novo_estado
        game.historico_lances = list(game.historico_lances) + [san]

        # Cria registro de lance
        move = MoveModel(
            id=str(uuid.uuid4()),
            game_id=game.game_id,
            san=san,
            fen_resultante=fen_resultante,
            jogador=jogador,
            numero_lance=numero_lance,
            timestamp=datetime.now(UTC),
        )
        self._session.add(move)
        # A sessão foi aberta externamente; o commit é responsabilidade do chamador
        return move

    async def create_game(
        self,
        lado_jogador_branco: str,
        lado_jogador_preto: str,
        fen_inicial: str,
    ) -> GameModel:
        """Cria e persiste uma nova partida. Utilitário para testes."""
        game = GameModel(
            game_id=str(uuid.uuid4()),
            estado="waiting",
            fen_atual=fen_inicial,
            turno="brancas",
            lado_jogador_branco=lado_jogador_branco,
            lado_jogador_preto=lado_jogador_preto,
            historico_lances=[],
            condicao_fim=None,
        )
        self._session.add(game)
        await self._session.flush()
        return game
