import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import create_engine

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    # L'engine non apre connessioni finché non serve: crearlo qui è sicuro anche a DB spento.
    engine = create_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await engine.dispose()

    app = FastAPI(
        title="Argo IAM",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.environment == "production" else "/api/docs",
        openapi_url=None if settings.environment == "production" else "/api/openapi.json",
    )
    app.state.engine = engine
    app.state.sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    @app.get("/api/health", tags=["system"])
    async def health(request: Request) -> JSONResponse:
        try:
            async with request.app.state.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except (SQLAlchemyError, OSError):
            logger.exception("health check: database non raggiungibile")
            return JSONResponse({"status": "degraded", "database": "unreachable"}, status_code=503)
        return JSONResponse({"status": "ok", "database": "ok"})

    return app
