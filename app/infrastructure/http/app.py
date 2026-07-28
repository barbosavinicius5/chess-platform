"""Aplicação FastAPI principal."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infrastructure.http.routers.moves import router as moves_router
from app.infrastructure.persistence.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await create_tables()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Chess Platform API", version="0.1.0", lifespan=lifespan)
    app.include_router(moves_router)
    return app


app = create_app()
