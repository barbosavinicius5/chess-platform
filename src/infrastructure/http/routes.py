"""FastAPI HTTP adapter — primary port for the chess platform API."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.application.create_game import CreateGameUseCase
from src.application.get_game import GetGameUseCase
from src.domain.game import GameNotFoundError
from src.domain.ports import EventEmitter, GameRepository, MetricsCounter

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class GameResponse(BaseModel):
    game_id: uuid.UUID
    estado: str
    fen: str


# ---------------------------------------------------------------------------
# Dependency providers (overridable in tests)
# ---------------------------------------------------------------------------


def get_repository() -> GameRepository:  # pragma: no cover
    """Provide the real SQLAlchemy repository.  Overridden in tests."""
    # NOTE: for a production setup use a proper lifespan/DI; this is minimal.
    raise NotImplementedError("Inject a real session via dependency override or lifespan.")


def get_event_emitter() -> EventEmitter:  # pragma: no cover
    from src.infrastructure.events import LogEventEmitter

    return LogEventEmitter()


def get_metrics_counter() -> MetricsCounter:  # pragma: no cover
    from src.infrastructure.metrics import InMemoryMetricsCounter

    return InMemoryMetricsCounter()


# Type aliases for injection
RepoDep = Annotated[GameRepository, Depends(get_repository)]
EmitterDep = Annotated[EventEmitter, Depends(get_event_emitter)]
MetricsDep = Annotated[MetricsCounter, Depends(get_metrics_counter)]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/games", response_model=GameResponse, status_code=status.HTTP_201_CREATED)
async def create_game(
    repo: RepoDep,
    emitter: EmitterDep,
    metrics: MetricsDep,
) -> GameResponse:
    use_case = CreateGameUseCase(repo, emitter, metrics)
    try:
        game = await use_case.execute()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao criar partida.",
        ) from exc
    return GameResponse(game_id=game.game_id, estado=game.estado.value, fen=game.fen)


@router.get("/games/{game_id}", response_model=GameResponse)
async def get_game(
    game_id: uuid.UUID,
    repo: RepoDep,
) -> GameResponse:
    use_case = GetGameUseCase(repo)
    try:
        game = await use_case.execute(game_id)
    except GameNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Partida não encontrada"},
        ) from exc
    return GameResponse(game_id=game.game_id, estado=game.estado.value, fen=game.fen)
