import httpx

from app.core.config import Settings
from app.main import create_app


async def get_health(database_url: str) -> httpx.Response:
    app = create_app(Settings(database_url=database_url))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
    await app.state.engine.dispose()
    return response


async def test_health_ok(migrated_database: str) -> None:
    response = await get_health(migrated_database)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


async def test_health_reports_unreachable_database() -> None:
    # Porta 1: nessun servizio in ascolto, connessione rifiutata subito.
    response = await get_health("postgresql+asyncpg://argo:x@127.0.0.1:1/none")
    assert response.status_code == 503
    assert response.json()["database"] == "unreachable"
