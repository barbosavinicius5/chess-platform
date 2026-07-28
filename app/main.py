"""Application entry point — FastAPI app factory."""

import logging
import logging.config

from fastapi import FastAPI

from app.infrastructure.database import build_engine, build_session_factory
from app.infrastructure.http.router import router
from app.settings import Settings

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "logging.Formatter",
            "fmt": '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        }
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    logging.config.dictConfig(LOGGING_CONFIG)

    app = FastAPI(title="URL Shortener", version="0.1.0")

    engine = build_engine(settings)
    session_factory = build_session_factory(engine)

    app.state.engine = engine
    app.state.session_factory = session_factory

    app.include_router(router)

    return app


app = create_app()
