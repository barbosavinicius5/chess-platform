"""Application entry-point: assembles the FastAPI app."""

from __future__ import annotations

from fastapi import FastAPI

from src.infrastructure.http.routes import router

app = FastAPI(title="Chess Platform", version="0.1.0")
app.include_router(router)