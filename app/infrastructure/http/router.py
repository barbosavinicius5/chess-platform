"""FastAPI HTTP adapter — routes for URL shortener."""

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl

from app.application.use_cases import CreateLinkUseCase, GetStatsUseCase, IncrementClickUseCase, ResolveLinkUseCase
from app.domain.exceptions import LinkNotFoundError
from app.infrastructure.http.dependencies import (
    get_create_use_case,
    get_increment_use_case,
    get_resolve_use_case,
    get_stats_use_case,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────


class CreateLinkRequest(BaseModel):
    short_code: str
    original_url: HttpUrl


class CreateLinkResponse(BaseModel):
    short_code: str
    original_url: str


class StatsResponse(BaseModel):
    short_code: str
    clicks: int


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/urls", response_model=CreateLinkResponse, status_code=201)
async def create_link(
    body: CreateLinkRequest,
    use_case: Annotated[CreateLinkUseCase, Depends(get_create_use_case)],
) -> CreateLinkResponse:
    link = await use_case.execute(body.short_code, str(body.original_url))
    return CreateLinkResponse(short_code=link.short_code, original_url=link.original_url)


@router.get("/urls/{short_code}/stats", response_model=StatsResponse)
async def get_stats(
    short_code: str,
    use_case: Annotated[GetStatsUseCase, Depends(get_stats_use_case)],
) -> StatsResponse:
    try:
        clicks = await use_case.execute(short_code)
    except LinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Short code '{short_code}' not found") from exc
    return StatsResponse(short_code=short_code, clicks=clicks)


@router.get("/{short_code}")
async def redirect(
    short_code: str,
    background_tasks: BackgroundTasks,
    resolve_use_case: Annotated[ResolveLinkUseCase, Depends(get_resolve_use_case)],
    increment_use_case: Annotated[IncrementClickUseCase, Depends(get_increment_use_case)],
) -> RedirectResponse:
    try:
        link = await resolve_use_case.execute(short_code)
    except LinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Short code '{short_code}' not found") from exc

    # Decoupled click counting — does NOT block the redirect response
    background_tasks.add_task(increment_use_case.execute, short_code)

    return RedirectResponse(url=link.original_url, status_code=302)
