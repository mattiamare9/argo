from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditEvent
from app.modules.audit.router import router


@pytest.fixture
async def client(session: AsyncSession, migrated_database: str):
    """Come `api`, ma con il router audit incluso (finché main.py non lo include)."""
    from app.core.config import Settings
    from app.db.session import get_db
    from app.main import create_app

    app = create_app(
        Settings(
            database_url=migrated_database,
            secrets_key=None,
            oidc_client_secret=None,
            keycloak_backend_client_secret=None,
        )
    )
    if "/api/audit" not in app.openapi()["paths"]:
        app.include_router(router)
    app.dependency_overrides[get_db] = lambda: session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    await app.state.engine.dispose()


async def seed(session: AsyncSession) -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for i, (actor, action, outcome, target) in enumerate(
        [
            ("user:anna", "employee.created", "success", "E001"),
            ("worker", "identity.disable", "failure", "E002"),
            ("agent:Excel-HR", "sync.snapshot_applied", "success", None),
        ]
    ):
        session.add(
            AuditEvent(
                actor=actor,
                action=action,
                outcome=outcome,
                target_id=target,
                occurred_at=base + timedelta(minutes=i),
                details={},
            )
        )
    await session.flush()


async def test_requires_login_and_role(client: httpx.AsyncClient, login_as) -> None:
    assert (await client.get("/api/audit")).status_code == 401
    await login_as(client)
    assert (await client.get("/api/audit")).status_code == 403
    await login_as(client, "iam-owner", username="owner")
    assert (await client.get("/api/audit")).status_code == 200


async def test_newest_first_and_filters(
    client: httpx.AsyncClient, session: AsyncSession, login_as
) -> None:
    await login_as(client, "iam-owner")
    await seed(session)

    body = (await client.get("/api/audit")).json()
    assert [i["action"] for i in body["items"]][:3] == [
        "sync.snapshot_applied",
        "identity.disable",
        "employee.created",
    ]
    assert body["total"] >= 3

    r = await client.get("/api/audit", params={"search": "excel-hr"})
    assert [i["actor"] for i in r.json()["items"]] == ["agent:Excel-HR"]
    r = await client.get("/api/audit", params={"search": "E002"})
    assert [i["action"] for i in r.json()["items"]] == ["identity.disable"]
    r = await client.get("/api/audit", params={"search": "EMPLOYEE.CREATED"})
    assert r.json()["total"] == 1

    r = await client.get("/api/audit", params={"outcome": "failure", "search": "worker"})
    assert [i["outcome"] for i in r.json()["items"]] == ["failure"]


async def test_pagination(client: httpx.AsyncClient, session: AsyncSession, login_as) -> None:
    await login_as(client, "iam-owner")
    await seed(session)
    r = await client.get("/api/audit", params={"search": "e", "page_size": 2, "page": 2})
    body = r.json()
    assert (body["page"], body["page_size"], body["total"]) == (2, 2, 3)
    assert [i["action"] for i in body["items"]] == ["employee.created"]
    assert (await client.get("/api/audit", params={"page_size": 101})).status_code == 422
