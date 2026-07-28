from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from chess.application.use_cases.get_game import AccessDenied, GameNotFound, GetGameUseCase
from chess.infrastructure.http.dependencies import get_get_game_use_case, get_player_id
from chess.infrastructure.http.schemas import GameResponse

router = APIRouter()


@router.get("/games/{game_id}", response_model=GameResponse)
async def get_game(
    game_id: str,
    player_id: str = Depends(get_player_id),
    use_case: GetGameUseCase = Depends(get_get_game_use_case),
) -> GameResponse:
    try:
        game = await use_case.execute(game_id, player_id)
    except GameNotFound:
        raise HTTPException(status_code=404, detail="Partida não encontrada")
    except AccessDenied:
        raise HTTPException(status_code=403, detail="Acesso não permitido")

    return GameResponse(
        game_id=game.game_id,
        status=game.status,
        turn=game.turn,
        fen=game.fen,
        moves=[m.san for m in sorted(game.moves, key=lambda x: x.order)],
    )