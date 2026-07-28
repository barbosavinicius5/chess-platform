"""Application services — orchestrate domain objects and output ports."""

import logging

from chess.domain.models import Game, Move, MoveResult
from chess.domain.ports import IGameNotifier

logger = logging.getLogger(__name__)


class GameService:
    """Use-case orchestrator for chess game actions.

    Depends on the *IGameNotifier* port — never on a concrete WebSocket adapter.
    """

    def __init__(self, notifier: IGameNotifier) -> None:
        self._notifier = notifier
        # In-memory store for this task. A real impl would use a repository port.
        self._games: dict[str, Game] = {}

    # ------------------------------------------------------------------
    # Game lifecycle
    # ------------------------------------------------------------------

    def create_game(self, game_id: str, white_player_id: str, black_player_id: str) -> Game:
        """Create and persist (in-memory) a new game in ONGOING status."""
        from chess.domain.models import GameStatus

        game = Game(
            game_id=game_id,
            white_player_id=white_player_id,
            black_player_id=black_player_id,
        )
        game.status = GameStatus.ONGOING
        self._games[game_id] = game
        logger.info("game_created", extra={"game_id": game_id})
        return game

    def get_game(self, game_id: str) -> Game | None:
        return self._games.get(game_id)

    # ------------------------------------------------------------------
    # Move submission — the core use-case for this task
    # ------------------------------------------------------------------

    async def submit_move(self, game_id: str, move: Move) -> MoveResult:
        """Validate and apply a move; fan-out FEN to clients if accepted.

        Returns the MoveResult so callers (e.g. the HTTP/WS adapter) can
        communicate the outcome to the requesting player.
        """
        game = self._games.get(game_id)
        if game is None:
            logger.warning("submit_move.game_not_found", extra={"game_id": game_id})
            return MoveResult.REJECTED

        result = game.apply_move(move)

        if result == MoveResult.ACCEPTED:
            # Rule: propagate ONLY after a lance is accepted.
            logger.debug(
                "submit_move.accepted",
                extra={"game_id": game_id, "uci": move.uci, "fen": game.fen},
            )
            await self._notifier.notify_move_accepted(game_id, game.fen)
        else:
            # Rule: do NOT propagate or log lance_propagado on rejection.
            logger.debug(
                "submit_move.rejected",
                extra={"game_id": game_id, "uci": move.uci},
            )

        return result
