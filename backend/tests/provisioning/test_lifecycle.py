from datetime import UTC, datetime, timedelta

import pytest

from app.modules import jobs, provisioning
from app.modules.employees import AppliedChange, ChangeKind
from app.modules.identity import IdentityError, IdentityUser, UserNotFound


def later(days: float) -> datetime:
    return datetime.now(UTC) + timedelta(days=days)


class FakeIdentity:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.failing: set[str] = set()
        self.users: set[str] = set()

    def _call(self, name: str, *args) -> None:
        self.calls.append((name, *args))
        if name in self.failing:
            raise IdentityError(f"{name} non disponibile")

    async def ensure_user(self, user: IdentityUser) -> None:
        self._call("ensure_user", user.employee_id)
        self.users.add(user.employee_id)

    async def set_enabled(self, employee_id: str, enabled: bool) -> None:
        self._call("set_enabled", employee_id, enabled)
        if employee_id not in self.users:
            raise UserNotFound(employee_id)

    async def logout(self, employee_id: str) -> None:
        self._call("logout", employee_id)

    async def send_enrollment(self, employee_id: str) -> None:
        self._call("send_enrollment", employee_id)

    async def grant_role(self, employee_id: str, role: str) -> None:
        self._call("grant_role", employee_id, role)


class SameSession:
    """Fa da sessionmaker negli handler, riusando la sessione transazionale del test."""

    def __init__(self, session) -> None:
        self.session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *exc) -> None:
        return None


@pytest.fixture
def identity() -> FakeIdentity:
    return FakeIdentity()


@pytest.fixture
def handlers(identity, session):
    return provisioning.build_handlers(identity, SameSession(session))


def change(eid: str, kind: ChangeKind, status: str = "ACTIVE") -> AppliedChange:
    return AppliedChange(eid, kind, status, False, f"{eid.lower()}@example.com", "Nome", eid)


async def drain(session, handlers, now: datetime | None = None) -> None:
    while await jobs.run_once(session, handlers, now=now):
        pass


async def runs(session) -> dict[str, provisioning.RunOut]:
    return {r.employee_id: r for r in await provisioning.list_runs(session, only_open=False)}


async def test_new_active_employee_is_onboarded(session, handlers, identity) -> None:
    await provisioning.on_changes(session, [change("E001", ChangeKind.CREATED)], triggered_by="t")
    await drain(session, handlers)
    assert ("send_enrollment", "E001") in identity.calls
    assert (await runs(session))["E001"].status == "completed"


async def test_new_inactive_employee_gets_no_account(session, handlers, identity) -> None:
    created = [change("E001", ChangeKind.CREATED, "INACTIVE")]
    assert await provisioning.on_changes(session, created, triggered_by="t") == []


async def test_offboarding_runs_every_step(session, handlers, identity) -> None:
    identity.users.add("E001")
    await provisioning.on_changes(
        session, [change("E001", ChangeKind.DEACTIVATED, "INACTIVE")], triggered_by="t"
    )
    await drain(session, handlers)
    assert ("set_enabled", "E001", False) in identity.calls
    assert ("logout", "E001") in identity.calls
    run = (await runs(session))["E001"]
    assert run.kind == "offboarding"
    assert run.status == "completed"
    assert [s.status for s in run.steps] == ["SUCCESS"] * 3


async def test_failed_step_does_not_undo_the_others_and_is_retried(
    session, handlers, identity
) -> None:
    identity.users.add("E001")
    identity.failing.add("logout")
    await provisioning.on_changes(
        session, [change("E001", ChangeKind.DEACTIVATED, "INACTIVE")], triggered_by="t"
    )
    await drain(session, handlers)
    run = (await runs(session))["E001"]
    statuses = {s.kind: s.status for s in run.steps}
    assert statuses["identity.disable"] == "SUCCESS"  # già riuscita, resta riuscita
    assert statuses["identity.logout"] == "RETRYING"
    assert run.status == "in_progress"

    identity.failing.clear()
    await drain(session, handlers, now=later(1))
    assert (await runs(session))["E001"].status == "completed"


async def test_exhausted_retries_leave_a_visible_partial_offboarding(
    session, handlers, identity
) -> None:
    identity.users.add("E001")
    identity.failing.add("logout")
    await provisioning.on_changes(
        session, [change("E001", ChangeKind.DEACTIVATED, "INACTIVE")], triggered_by="t"
    )
    for day in range(12):
        await drain(session, handlers, now=later(day))
    run = (await provisioning.list_runs(session, only_open=True))[0]
    assert run.status == "partial"
    failed = next(s for s in run.steps if s.kind == "identity.logout")
    assert failed.status == "FAILED"
    assert "logout non disponibile" in failed.last_error


async def test_offboarding_without_account_succeeds(session, handlers) -> None:
    await provisioning.on_changes(
        session, [change("E404", ChangeKind.DEACTIVATED, "INACTIVE")], triggered_by="t"
    )
    await drain(session, handlers)
    assert (await runs(session))["E404"].status == "completed"


async def test_profile_update_of_inactive_employee_is_ignored(session) -> None:
    updated = [change("E001", ChangeKind.UPDATED, "INACTIVE")]
    assert await provisioning.on_changes(session, updated, triggered_by="t") == []


async def test_snapshot_to_offboarding_end_to_end(api, session, login_as, identity, handlers):
    from app.modules import synchronization

    key = await synchronization.create_agent(session, "e2e")
    headers = {"Authorization": f"Bearer {key}"}

    def body(status: str) -> dict:
        record = {
            "employee_id": "E001",
            "email": "e001@example.com",
            "first_name": "Mario",
            "last_name": "Rossi",
            "status": status,
        }
        import uuid

        return {
            "snapshot_id": str(uuid.uuid4()),
            "source": "excel-hr",
            "read_at": "2026-11-21T10:00:00Z",
            "records": [record],
        }

    await api.post("/api/v1/sync/snapshots", json=body("ACTIVE"), headers=headers)
    await drain(session, handlers)
    await api.post("/api/v1/sync/snapshots", json=body("INACTIVE"), headers=headers)
    await drain(session, handlers)

    await login_as(api, "iam-owner")
    all_runs = (await api.get("/api/provisioning/runs")).json()
    assert [(r["kind"], r["status"]) for r in all_runs] == [
        ("offboarding", "completed"),
        ("onboarding", "completed"),
    ]
    assert ("set_enabled", "E001", False) in identity.calls


async def test_offboarding_revokes_dashboard_sessions(api, session, login_as, handlers) -> None:
    await login_as(api, "iam-owner", username="e001")
    assert (await api.get("/api/auth/me")).status_code == 200
    await provisioning.on_changes(
        session, [change("E001", ChangeKind.DEACTIVATED, "INACTIVE")], triggered_by="t"
    )
    await drain(session, handlers)
    assert (await api.get("/api/auth/me")).status_code == 401


async def test_manual_step_resolution_requires_role(api, session, login_as) -> None:
    import uuid

    response = await api.post(
        f"/api/provisioning/jobs/{uuid.uuid4()}/retry", headers={"X-Argo-CSRF": "1"}
    )
    assert response.status_code == 401
    await login_as(api, "iam-owner")
    response = await api.post(
        f"/api/provisioning/jobs/{uuid.uuid4()}/retry", headers={"X-Argo-CSRF": "1"}
    )
    assert response.status_code == 403  # il retry è solo per l'amministratore


async def test_board_shows_one_key_per_employee(api, session, login_as, handlers) -> None:
    from app.modules import employees
    from app.modules.employees import EmployeeRecord

    records = [
        EmployeeRecord(employee_id=e, email=f"{e}@x.it", first_name="N", last_name=e, status=s)
        for e, s in [("A1", "ACTIVE"), ("A2", "ACTIVE"), ("I1", "INACTIVE")]
    ]
    applied = await employees.apply_changes(
        session, await employees.plan_changes(session, records), source="t", actor="t"
    )
    await provisioning.on_changes(session, applied, triggered_by="t")
    await drain(session, handlers)
    # A2 riceve un offboarding che resta in corso: la chiave è in ambra.
    await provisioning.on_changes(
        session, [change("A2", ChangeKind.DEACTIVATED, "INACTIVE")], triggered_by="t"
    )
    await login_as(api, "iam-owner")
    plates = {
        p["employee_id"]: p["keys"][0]["state"]
        for p in (await api.get("/api/provisioning/board")).json()
    }
    assert plates == {"A1": "hung", "A2": "pending", "I1": "returned"}


def test_key_state_rules() -> None:
    from app.modules.provisioning.service import key_state

    assert key_state("ACTIVE", "completed") == "hung"
    assert key_state("ACTIVE", None) == "pending"
    assert key_state("INACTIVE", None) == "returned"
    assert key_state("INACTIVE", "completed") == "returned"
    assert key_state("INACTIVE", "partial") == "pending"
