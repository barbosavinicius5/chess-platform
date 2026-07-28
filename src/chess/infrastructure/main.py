from __future__ import annotations

from fastapi import FastAPI

from chess.infrastructure.http.routers.games import router as games_router


def create_app() -> FastAPI:
    app = FastAPI(title="Chess Platform", version="0.1.0")
    app.include_router(games_router)
    return app


app = create_app()