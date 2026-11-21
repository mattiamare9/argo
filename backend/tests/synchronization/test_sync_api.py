import uuid

import pytest

from app.modules import synchronization

HEADERS_CSRF = {"X-Argo-CSRF": "1"}


def rec(eid: str, status: str = "ACTIVE", email: str | None = None) -> dict:
    return {
        "employee_id": eid,
        "email": email or f"{eid.lower()}@example.com",
        "first_name": "Nome",
        "last_name": eid,
        "status": status,
    }


def snapshot(*records: dict, snapshot_id: str | None = None) -> dict:
    return {
        "snapshot_id": snapshot_id or str(uuid.uuid4()),
        "source": "excel-hr",
        "read_at": "2026-11-21T10:42:00Z",
        "records": list(records),
    }


@pytest.fixture
async def agent_key(session) -> str:
    return await synchronization.create_agent(session, f"agent-{uuid.uuid4().hex[:6]}")


@pytest.fixture
def send(api, agent_key):
    async def _send(body: dict):
        return await api.post(
            "/api/v1/sync/snapshots", json=body, headers={"Authorization": f"Bearer {agent_key}"}
        )

    return _send


async def test_invalid_agent_key_is_rejected(api) -> None:
    response = await api.post(
        "/api/v1/sync/snapshots",
        json=snapshot(rec("E001")),
        headers={"Authorization": "Bearer sbagliata"},
    )
    assert response.status_code == 401


async def test_first_snapshot_creates_employees(send) -> None:
    response = await send(snapshot(rec("E001"), rec("E002", "INACTIVE")))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "applied"
    assert body["summary"]["created"] == 2


async def test_same_snapshot_id_is_idempotent(send) -> None:
    body = snapshot(rec("E001"))
    assert (await send(body)).json()["status"] == "applied"
    again = (await send(body)).json()
    assert again["status"] == "duplicate"
    assert again["summary"]["created"] == 1


async def test_missing_employee_is_never_deactivated(send, api, login_as) -> None:
    await send(snapshot(rec("E001"), rec("E002")))
    body = (await send(snapshot(rec("E001")))).json()
    assert body["summary"]["deactivated"] == 0
    assert body["summary"]["missing_from_source"] == 1
    await login_as(api, "iam-owner")
    employees = (await api.get("/api/employees", params={"status": "ACTIVE"})).json()
    assert employees["total"] == 2


async def test_explicit_deactivation_is_applied(send) -> None:
    await send(snapshot(rec("E001"), rec("E002")))
    body = (await send(snapshot(rec("E001", "INACTIVE"), rec("E002")))).json()
    assert body["status"] == "applied"
    assert body["summary"]["deactivated"] == 1


async def test_duplicate_ids_reject_whole_snapshot(send, api, login_as) -> None:
    response = await send(snapshot(rec("E001"), rec("e001", email="altra@example.com")))
    assert response.status_code == 422
    assert "duplicati" in response.json()["detail"]
    await login_as(api, "iam-admin")
    overview = (await api.get("/api/sync/overview")).json()
    assert overview["recent"][0]["status"] == "rejected"


async def test_invalid_status_value_is_422(send) -> None:
    response = await send(snapshot(rec("E001", status="ATTIVO")))
    assert response.status_code == 422


async def test_mass_deactivation_waits_for_confirmation(send, api, login_as) -> None:
    await send(snapshot(*(rec(f"E00{i}") for i in range(1, 6))))
    leaving = snapshot(*(rec(f"E00{i}", "INACTIVE") for i in range(1, 4)), rec("E004"), rec("E005"))
    body = (await send(leaving)).json()
    assert body["status"] == "pending_confirmation"

    await login_as(api, "iam-owner")
    assert (await api.get("/api/employees", params={"status": "INACTIVE"})).json()["total"] == 0
    overview = (await api.get("/api/sync/overview")).json()
    assert [d["employee_id"] for d in overview["pending"]["deactivations"]] == [
        "E001",
        "E002",
        "E003",
    ]

    response = await api.post(
        f"/api/sync/snapshots/{leaving['snapshot_id']}/confirm", headers=HEADERS_CSRF
    )
    assert response.status_code == 200
    assert response.json()["status"] == "applied"
    assert (await api.get("/api/employees", params={"status": "INACTIVE"})).json()["total"] == 3


async def test_cancelled_mass_deactivation_changes_nothing(send, api, login_as) -> None:
    await send(snapshot(*(rec(f"E00{i}") for i in range(1, 4))))
    leaving = snapshot(*(rec(f"E00{i}", "INACTIVE") for i in range(1, 4)))
    await send(leaving)
    await login_as(api, "iam-admin")
    response = await api.post(
        f"/api/sync/snapshots/{leaving['snapshot_id']}/cancel", headers=HEADERS_CSRF
    )
    assert response.json()["status"] == "cancelled"
    assert (await api.get("/api/employees", params={"status": "INACTIVE"})).json()["total"] == 0
    assert (await api.get("/api/sync/overview")).json()["pending"] is None


async def test_new_snapshot_supersedes_pending_one(send, api, login_as) -> None:
    await send(snapshot(*(rec(f"E00{i}") for i in range(1, 4))))
    first = snapshot(*(rec(f"E00{i}", "INACTIVE") for i in range(1, 4)))
    await send(first)
    await send(snapshot(*(rec(f"E00{i}") for i in range(1, 4))))
    await login_as(api, "iam-admin")
    response = await api.post(
        f"/api/sync/snapshots/{first['snapshot_id']}/confirm", headers=HEADERS_CSRF
    )
    assert response.status_code == 409


async def test_confirm_requires_csrf_and_role(send, api, login_as) -> None:
    await send(snapshot(*(rec(f"E00{i}") for i in range(1, 4))))
    leaving = snapshot(*(rec(f"E00{i}", "INACTIVE") for i in range(1, 4)))
    await send(leaving)
    url = f"/api/sync/snapshots/{leaving['snapshot_id']}/confirm"
    assert (await api.post(url, headers=HEADERS_CSRF)).status_code == 401
    await login_as(api)  # autenticato senza ruoli
    assert (await api.post(url, headers=HEADERS_CSRF)).status_code == 403


async def test_agent_status_error_is_shown_and_cleared(send, api, agent_key, login_as) -> None:
    headers = {"Authorization": f"Bearer {agent_key}"}
    response = await api.post(
        "/api/v1/sync/agent-status",
        json={"ok": False, "message": "Colonna obbligatoria mancante: status"},
        headers=headers,
    )
    assert response.status_code == 204
    await login_as(api, "iam-admin")
    (agent,) = (await api.get("/api/sync/overview")).json()["agents"]
    assert agent["last_error"] == "Colonna obbligatoria mancante: status"
    await send(snapshot(rec("E001")))
    (agent,) = (await api.get("/api/sync/overview")).json()["agents"]
    assert agent["last_error"] is None


async def test_email_swap_in_one_snapshot_is_allowed(send) -> None:
    await send(snapshot(rec("E001", email="a@example.com"), rec("E002", email="b@example.com")))
    swap = snapshot(rec("E001", email="b@example.com"), rec("E002", email="a@example.com"))
    body = (await send(swap)).json()
    assert body["status"] == "applied"
    assert body["summary"]["updated"] == 2


async def test_employees_list_requires_role(api) -> None:
    assert (await api.get("/api/employees")).status_code == 401


async def test_second_confirmation_is_rejected(send, api, login_as) -> None:
    await send(snapshot(*(rec(f"E00{i}") for i in range(1, 4))))
    leaving = snapshot(*(rec(f"E00{i}", "INACTIVE") for i in range(1, 4)))
    await send(leaving)
    await login_as(api, "iam-admin")
    url = f"/api/sync/snapshots/{leaving['snapshot_id']}/confirm"
    assert (await api.post(url, headers=HEADERS_CSRF)).status_code == 200
    assert (await api.post(url, headers=HEADERS_CSRF)).status_code == 409  # niente doppio apply


async def test_admin_rotates_agent_key_from_dashboard(api, login_as) -> None:
    await login_as(api, "iam-owner")
    created = await api.post("/api/sync/agents", json={"name": "hr-2"}, headers=HEADERS_CSRF)
    assert created.status_code == 403  # solo l'amministratore

    await login_as(api, "iam-admin", username="admin2")
    created = await api.post("/api/sync/agents", json={"name": "hr-2"}, headers=HEADERS_CSRF)
    assert created.status_code == 201
    key = created.json()["key"]
    agent_headers = {"Authorization": f"Bearer {key}"}
    ok = await api.post("/api/v1/sync/snapshots", json=snapshot(rec("E001")), headers=agent_headers)
    assert ok.status_code == 200

    again = await api.post("/api/sync/agents", json={"name": "hr-2"}, headers=HEADERS_CSRF)
    assert again.status_code == 409
    revoked = await api.post("/api/sync/agents/hr-2/revoke", headers=HEADERS_CSRF)
    assert revoked.status_code == 204
    after = await api.post(
        "/api/v1/sync/snapshots", json=snapshot(rec("E002")), headers=agent_headers
    )
    assert after.status_code == 401
