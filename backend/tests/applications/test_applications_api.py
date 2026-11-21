from cryptography.fernet import Fernet

from app.core.config import Settings
from app.modules import applications

CSRF = {"X-Argo-CSRF": "1"}
SCIM = {
    "slug": "crm",
    "name": "CRM",
    "connector": "scim",
    "config": {"base_url": "https://crm.test/scim/v2"},
}


async def test_owner_reads_but_cannot_write(api, login_as) -> None:
    await login_as(api, "iam-owner")
    assert (await api.get("/api/applications")).status_code == 200
    assert (await api.post("/api/applications", json=SCIM, headers=CSRF)).status_code == 403


async def test_anonymous_is_rejected(api) -> None:
    assert (await api.get("/api/applications")).status_code == 401


async def test_writes_require_csrf(api, login_as) -> None:
    await login_as(api, "iam-admin")
    assert (await api.post("/api/applications", json=SCIM)).status_code == 403


async def test_admin_crud_and_audit(api, session, login_as) -> None:
    await login_as(api, "iam-admin")
    manual = {"slug": "fatture", "name": "FatturaFacile", "connector": "manual"}
    created = await api.post("/api/applications", json=manual, headers=CSRF)
    assert created.status_code == 201
    app_id = created.json()["id"]
    assert (await api.post("/api/applications", json=manual, headers=CSRF)).status_code == 409

    patched = await api.patch(
        f"/api/applications/{app_id}", json={"name": "Fatture", "enabled": False}, headers=CSRF
    )
    assert patched.json()["name"] == "Fatture"
    assert patched.json()["enabled"] is False
    assert (await api.get("/api/applications")).json()[0]["slug"] == "fatture"

    assert (await api.delete(f"/api/applications/{app_id}", headers=CSRF)).status_code == 204
    assert (await api.delete(f"/api/applications/{app_id}", headers=CSRF)).status_code == 404

    from sqlalchemy import select

    from app.modules.audit.models import AuditEvent

    actions = [
        e.action
        for e in await session.scalars(
            select(AuditEvent).where(AuditEvent.target_type == "application")
        )
    ]
    assert sorted(actions) == ["application.create", "application.delete", "application.update"]


async def test_invalid_config_is_rejected(api, login_as) -> None:
    await login_as(api, "iam-admin")
    bad = {**SCIM, "config": {}}
    assert (await api.post("/api/applications", json=bad, headers=CSRF)).status_code == 422
    bad_slug = {**SCIM, "slug": "CRM!"}
    assert (await api.post("/api/applications", json=bad_slug, headers=CSRF)).status_code == 422


async def test_secret_without_key_is_409(api, login_as) -> None:
    await login_as(api, "iam-admin")
    response = await api.post("/api/applications", json={**SCIM, "secret": "tok"}, headers=CSRF)
    assert response.status_code == 409
    assert "ARGO_SECRETS_KEY" in response.json()["detail"]


async def test_secret_is_never_returned_nor_audited(api, session, login_as) -> None:
    api._transport.app.state.settings = Settings(
        database_url="x", secrets_key=Fernet.generate_key().decode()
    )
    await login_as(api, "iam-admin")
    created = await api.post(
        "/api/applications", json={**SCIM, "secret": "tok-segreto"}, headers=CSRF
    )
    body = created.json()
    assert body["has_secret"] is True
    assert "secret" not in body and "tok-segreto" not in created.text
    app_id = body["id"]
    assert "tok-segreto" not in (await api.get("/api/applications")).text

    stored = await applications.get_application(session, app_id)
    assert stored.secret_ciphertext and "tok-segreto" not in stored.secret_ciphertext

    cleared = await api.patch(f"/api/applications/{app_id}", json={"secret": None}, headers=CSRF)
    assert cleared.json()["has_secret"] is False
    kept = await api.patch(f"/api/applications/{app_id}", json={"name": "CRM 2"}, headers=CSRF)
    assert kept.json()["has_secret"] is False  # senza "secret" nel body resta com'è

    from sqlalchemy import select

    from app.modules.audit.models import AuditEvent

    events = await session.scalars(
        select(AuditEvent).where(AuditEvent.target_type == "application")
    )
    assert all("tok-segreto" not in str(e.details) for e in events)


async def test_changing_scim_address_drops_the_token(session, login_as) -> None:
    from cryptography.fernet import Fernet

    from app.core.config import Settings
    from app.modules.applications import service
    from app.modules.applications.schemas import ApplicationCreate, ApplicationUpdate

    settings = Settings(database_url="x", secrets_key=Fernet.generate_key().decode())
    created = await service.create(
        session,
        settings,
        ApplicationCreate(
            slug="crm2",
            name="CRM",
            connector="scim",
            config={"base_url": "https://crm.example/scim/v2"},
            secret="tok",
        ),
        actor="t",
    )
    assert created.has_secret
    moved = await service.update(
        session,
        settings,
        created.id,
        ApplicationUpdate(config={"base_url": "https://altro.example/scim/v2"}),
        actor="t",
    )
    assert not moved.has_secret  # il token non viene inviato al nuovo indirizzo
