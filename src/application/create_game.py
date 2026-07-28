"""Use case: create a new chess game."""

from __future__ import annotations

import datetime

from src.domain.game import Game
from src.domain.ports import EventEmitter, GameRepository, MetricsCounter


class CreateGameUseCase:
    """
    Orchestrates the creation of a new Game.

    Atomicity guarantee:
        - The event and metric are emitted ONLY after a successful repository commit.
        - If ``repository.save`` raises, neither the emitter nor the counter is called.
    """

    def __init__(
        self,
        repository: GameRepository,
        event_emitter: EventEmitter,
        metrics_counter: MetricsCounter,
    ) -> None:
        self._repo = repository
        self._emitter = event_emitter
        self._metrics = metrics_counter

    async def execute(self) -> Game:
        game = Game.create_new()

        # Persist first — if this raises, side-effects are NOT triggered.
        await self._repo.save(game)

        # Side-effects after successful commit.
        await self._emitter.emit(
            "partida_criada",
            {
                "game_id": str(game.game_id),
                "estado": game.estado.value,
                "fen_inicial": game.fen,
                "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            },
        )
        await self._metrics.increment("partidas_ativas")

        return game