import json

import httpx
import pytest
from cryptography.fernet import Fernet

from app.core import secrets
from app.core.config import Settings
from app.modules import jobs, provisioning
from app.modules.applications import Application
from app.modules.employees import ChangeKind
from tests.provisioning.test_lifecycle import FakeIdentity, SameSession, change, drain, runs

SETTINGS = Settings(database_url="x", secrets_key=Fernet.generate_key().decode())


class FakeScim:
    """Server SCIM minimale: ricorda gli utenti e le chiamate."""

    def __init__(self) -> None:
        self.users = {"mario@x.it": {"id": "u1", "active": True}}
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.method == "GET":
            email = request.url.params["filter"].split('"')[1]
            user = self.users.get(email)
            return httpx.Response(200, json={"Resources": [user] if user else []})
        self.users["mario@x.it"]["active"] = json.loads(request.content)["Operations"][0]["value"]
        return httpx.Response(200, json={})


@pytest.fixture
def scim_server() -> FakeScim:
    return FakeScim()


@pytest.fixture
def handlers(session, scim_server):
    http = httpx.AsyncClient(transport=httpx.MockTransport(scim_server))
    identity = FakeIdentity()
    identity.users.add("E001")  # l'account aziendale esiste: la disattivazione riesce
    return provisioning.build_handlers(identity, SameSession(session), SETTINGS, http)


async def add_apps(session) -> tuple[Application, Application]:
    manual = Application(slug="fatture", name="FatturaFacile", connector="manual", config={})
    scim = Application(
        slug="crm",
        name="CRM",
        connector="scim",
        config={"base_url": "https://crm.test/scim"},
        secret_ciphertext=secrets.encrypt(SETTINGS, "tok"),
    )
    session.add_all([manual, scim])
    await session.flush()
    return manual, scim


def mario(kind: ChangeKind = ChangeKind.DEACTIVATED, status: str = "INACTIVE"):
    c = change("E001", kind, status)
    return type(c)(c.employee_id, c.kind, c.status, False, "mario@x.it", "Mario", "Rossi")


async def test_offboarding_with_two_apps_is_partial_until_manual_step_is_resolved(
    session, handlers, scim_server
) -> None:
    await add_apps(session)
    await provisioning.on_changes(session, [mario()], triggered_by="t")
    await drain(session, handlers)

    run = (await runs(session))["E001"]
    steps = {s.label: s.status for s in run.steps}
    assert len(run.steps) == 5
    assert steps["Account CRM"] == "SUCCESS"
    assert steps["Account FatturaFacile"] == "MANUAL_PENDING"
    assert run.status == "partial"
    assert scim_server.users["mario@x.it"]["active"] is False

    manual = next(s for s in run.steps if s.label == "Account FatturaFacile")
    assert "Disattiva a mano" in manual.last_error
    await jobs.resolve_manual(session, manual.job_id, by="admin")
    assert (await runs(session))["E001"].status == "completed"


async def test_onboarding_provisions_apps_and_profile_update_does_not(
    session, handlers, scim_server
) -> None:
    await add_apps(session)
    await provisioning.on_changes(session, [mario(ChangeKind.CREATED, "ACTIVE")], triggered_by="t")
    run = (await runs(session))["E001"]
    assert sorted(s.kind for s in run.steps) == [
        "app.provision",
        "app.provision",
        "identity.provision",
    ]
    await drain(session, handlers)
    assert scim_server.users["mario@x.it"]["active"] is True

    await provisioning.on_changes(session, [mario(ChangeKind.UPDATED, "ACTIVE")], triggered_by="t")
    updated = [
        r
        for r in await provisioning.list_runs(session, only_open=False)
        if r.kind == "profile_update"
    ]
    assert [s.kind for s in updated[0].steps] == ["identity.update_profile"]


async def test_disabled_apps_get_no_jobs_and_deleted_apps_need_manual_check(
    session, handlers
) -> None:
    manual, scim = await add_apps(session)
    scim.enabled = False
    await session.flush()
    await provisioning.on_changes(session, [mario()], triggered_by="t")
    assert len((await runs(session))["E001"].steps) == 4  # 3 identità + solo l'app abilitata

    await session.delete(manual)
    await session.flush()
    await drain(session, handlers)
    # L'app non è più gestita: l'account potrebbe essere ancora aperto, serve una verifica.
    run = (await runs(session))["E001"]
    assert run.status == "partial"
    (step,) = [s for s in run.steps if s.kind == "app.deprovision"]
    assert step.status == "MANUAL_PENDING"


async def test_board_has_a_key_per_enabled_app(api, session, login_as, handlers) -> None:
    manual, _ = await add_apps(session)
    await provisioning.on_changes(session, [mario(ChangeKind.CREATED, "ACTIVE")], triggered_by="t")
    await drain(session, handlers)
    await login_as(api, "iam-owner")

    def keys(plate: dict) -> dict[str, str]:
        return {k["name"]: k["state"] for k in plate["keys"]}

    from app.modules import employees
    from app.modules.employees import EmployeeRecord

    # E001 non esiste in anagrafica: la creo; E002 attivo senza job, E003 inattivo senza job.
    records = [
        EmployeeRecord(employee_id=e, email=f"{e}@x.it", first_name="N", last_name=e, status=s)
        for e, s in [("E001", "ACTIVE"), ("E002", "ACTIVE"), ("E003", "INACTIVE")]
    ]
    await employees.apply_changes(
        session, await employees.plan_changes(session, records), source="t", actor="t"
    )
    plates = {p["employee_id"]: keys(p) for p in (await api.get("/api/provisioning/board")).json()}
    assert plates["E001"] == {
        "Account aziendale": "hung",
        "CRM": "hung",
        "FatturaFacile": "pending",  # passo manuale ancora da confermare
    }
    # Attivo mai toccato da Argo: account aziendale da verificare, app presunte attive.
    assert plates["E002"] == {
        "Account aziendale": "pending",
        "CRM": "hung",
        "FatturaFacile": "hung",
    }
    assert plates["E003"] == {
        "Account aziendale": "returned",
        "CRM": "returned",
        "FatturaFacile": "returned",
    }
