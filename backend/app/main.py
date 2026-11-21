import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import create_engine
from app.modules.applications.router import router as applications_router
from app.modules.audit.router import router as audit_router
from app.modules.employees.router import router as employees_router
from app.modules.identity import build_identity_provider
from app.modules.provisioning.router import router as provisioning_router
from app.modules.sessions.oidc import OidcClient, OidcConfig
from app.modules.sessions.router import router as auth_router
from app.modules.synchronization.router import agent_router, dashboard_router

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, http: httpx.AsyncClient | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    # L'engine non apre connessioni finché non serve: crearlo qui è sicuro anche a DB spento.
    engine = create_engine(settings.database_url)
    http = http or httpx.AsyncClient(timeout=10)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await http.aclose()
        await engine.dispose()

    app = FastAPI(
        title="Argo IAM",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.environment == "production" else "/api/docs",
        openapi_url=None if settings.environment == "production" else "/api/openapi.json",
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    app.state.http = http
    app.state.oidc = (
        OidcClient(
            OidcConfig(
                issuer=settings.oidc_issuer,
                client_id=settings.oidc_client_id,
                client_secret=settings.oidc_client_secret.get_secret_value(),
                redirect_uri=f"{settings.public_url}/api/auth/callback",
            ),
            http,
        )
        if settings.oidc_client_secret
        else None
    )
    # Usato dalle sessioni per riverificare ruoli e stato degli utenti (ADR-022).
    app.state.identity = (
        build_identity_provider(settings, http) if settings.keycloak_backend_client_secret else None
    )
    app.include_router(auth_router)
    app.include_router(audit_router)
    app.include_router(employees_router)
    app.include_router(agent_router)
    app.include_router(dashboard_router)
    app.include_router(provisioning_router)
    app.include_router(applications_router)

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
