"""Router HTTP para lances — POST /games/{game_id}/moves."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.submeter_lance import (
    ForaDeTurnoError,
    LanceRecusadoError,
    NaoParticipanteError,
    SubmeterLanceUseCase,
)
from app.infrastructure.http.dependencies import get_session
from app.infrastructure.persistence.game_repository import GameNotFoundError, GameRepository

router = APIRouter(prefix="/games", tags=["moves"])


# ── Schemas Pydantic ─────────────────────────────────────────────────────────


class SubmeterLanceRequest(BaseModel):
    san: str = Field(..., min_length=1, max_length=10, description="Lance em SAN (ex: e4, Nf3, O-O)")


class SubmeterLanceResponse(BaseModel):
    game_id: str
    fen_resultante: str
    status: str
    lado: str


class ErroResponse(BaseModel):
    razao: str


# ── Adaptador de UnitOfWork para a sessão ────────────────────────────────────


class _SessionUoW:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()


# ── Endpoint ─────────────────────────────────────────────────────────────────


@router.post(
    "/{game_id}/moves",
    response_model=SubmeterLanceResponse,
    responses={
        422: {"model": ErroResponse, "description": "Lance recusado ou fora de turno"},
        403: {"model": ErroResponse, "description": "Não participante"},
        404: {"model": ErroResponse, "description": "Partida não encontrada"},
    },
)
async def submeter_lance(  # noqa: B008
    game_id: str,
    body: SubmeterLanceRequest,
    x_player_id: str = Header(..., description="UUID do jogador (header X-Player-Id)"),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> SubmeterLanceResponse:
    """Submete um lance SAN em uma partida de xadrez."""
    repo = GameRepository(session)
    uow = _SessionUoW(session)
    use_case = SubmeterLanceUseCase(repo=repo, uow=uow)

    try:
        result = await use_case.execute(game_id=game_id, player_id=x_player_id, san=body.san)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"razao": str(exc)}) from exc
    except NaoParticipanteError as exc:
        raise HTTPException(status_code=403, detail={"razao": str(exc)}) from exc
    except ForaDeTurnoError as exc:
        raise HTTPException(status_code=422, detail={"razao": str(exc)}) from exc
    except LanceRecusadoError as exc:
        raise HTTPException(status_code=422, detail={"razao": exc.razao}) from exc

    return SubmeterLanceResponse(
        game_id=result.game_id,
        fen_resultante=result.fen_resultante,
        status=result.status,
        lado=result.lado,
    )
