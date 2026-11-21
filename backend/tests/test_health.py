from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

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
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"


async def test_health_reports_unreachable_database() -> None:
    # Porta 1: nessun servizio in ascolto, connessione rifiutata subito.
    response = await get_health("postgresql+asyncpg://argo:x@127.0.0.1:1/none")
    assert response.status_code == 503
    assert response.json()["database"] == "unreachable"


async def seed_heartbeat(database_url: str, age: timedelta | None) -> None:
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM worker_heartbeats"))
        if age is not None:
            await conn.execute(
                text("INSERT INTO worker_heartbeats VALUES ('w', :ts)"),
                {"ts": datetime.now(UTC) - age},
            )
    await engine.dispose()


async def test_health_worker_unknown_without_heartbeats(migrated_database: str) -> None:
    await seed_heartbeat(migrated_database, None)
    response = await get_health(migrated_database)
    assert response.status_code == 200
    assert response.json()["worker"] == "unknown"


async def test_health_worker_ok_with_recent_heartbeat(migrated_database: str) -> None:
    await seed_heartbeat(migrated_database, timedelta(seconds=10))
    response = await get_health(migrated_database)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "worker": "ok"}
    await seed_heartbeat(migrated_database, None)


async def test_health_503_when_worker_stale(migrated_database: str) -> None:
    await seed_heartbeat(migrated_database, timedelta(minutes=5))
    response = await get_health(migrated_database)
    await seed_heartbeat(migrated_database, None)
    assert response.status_code == 503
    assert response.json()["worker"] == "stale"
