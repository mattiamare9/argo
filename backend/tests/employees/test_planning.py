from sqlalchemy.ext.asyncio import AsyncSession

from app.modules import employees
from app.modules.employees import ChangeKind, EmployeeRecord


def rec(eid: str, status: str = "ACTIVE", email: str | None = None, first: str = "Mario"):
    return EmployeeRecord(
        employee_id=eid,
        email=email or f"{eid.lower()}@example.com",
        first_name=first,
        last_name="Rossi",
        status=status,
    )


def kinds(plan) -> dict[str, ChangeKind]:
    return {c.record.employee_id: c.kind for c in plan}


async def apply(session: AsyncSession, *records: EmployeeRecord):
    plan = await employees.plan_changes(session, list(records))
    return await employees.apply_changes(session, plan, source="excel-hr", actor="test")


async def test_new_employees_are_created(session) -> None:
    plan = await employees.plan_changes(session, [rec("E001"), rec("E002", "INACTIVE")])
    assert kinds(plan) == {"E001": ChangeKind.CREATED, "E002": ChangeKind.CREATED}


async def test_transitions_are_detected(session) -> None:
    await apply(session, rec("E001"), rec("E002", "INACTIVE"), rec("E003"), rec("E004"))
    plan = await employees.plan_changes(
        session,
        [rec("e001", "INACTIVE"), rec("E002"), rec("E003", first="Maria"), rec("E004")],
    )
    assert kinds(plan) == {
        "e001": ChangeKind.DEACTIVATED,  # chiave senza distinzione maiuscole/minuscole
        "E002": ChangeKind.REACTIVATED,
        "E003": ChangeKind.UPDATED,
        "E004": ChangeKind.UNCHANGED,
    }


async def test_deactivation_with_profile_change_keeps_both(session) -> None:
    await apply(session, rec("E001"))
    (change,) = await employees.plan_changes(
        session, [rec("E001", "INACTIVE", email="nuova@example.com")]
    )
    assert change.kind is ChangeKind.DEACTIVATED
    assert change.profile_changed


async def test_apply_persists_and_reports(session) -> None:
    applied = await apply(session, rec("E001"))
    assert applied[0].kind is ChangeKind.CREATED
    applied = await apply(session, rec("E001", "INACTIVE"))
    assert applied[0].kind is ChangeKind.DEACTIVATED
    page = await employees.list_employees(session, status="INACTIVE")
    assert [e.employee_id for e in page.items] == ["E001"]


async def test_email_is_stored_lowercase(session) -> None:
    await apply(session, rec("E001", email="Mario.Rossi@Example.com"))
    page = await employees.list_employees(session)
    assert page.items[0].email == "mario.rossi@example.com"


async def test_email_taken_by_another_employee_is_a_conflict(session) -> None:
    await apply(session, rec("E001", email="condivisa@example.com"))
    conflicts = await employees.find_email_conflicts(
        session, [rec("E002", email="CONDIVISA@example.com")]
    )
    assert conflicts == ["condivisa@example.com"]


async def test_email_moving_between_records_in_same_snapshot_is_allowed(session) -> None:
    await apply(session, rec("E001", email="a@example.com"))
    conflicts = await employees.find_email_conflicts(
        session, [rec("E001", email="b@example.com"), rec("E002", email="a@example.com")]
    )
    # E001 libera a@ nello stesso snapshot: non è un conflitto con dipendenti esterni.
    assert conflicts == []


async def test_missing_from_source_count(session) -> None:
    await apply(session, rec("E001"), rec("E002"))
    assert await employees.count_missing(session, [rec("E001")]) == 1


async def test_list_search_and_pagination(session) -> None:
    await apply(session, rec("E001", first="Anna"), rec("E002", first="Bruno"), rec("E003"))
    page = await employees.list_employees(session, search="brun")
    assert [e.employee_id for e in page.items] == ["E002"]
    page = await employees.list_employees(session, page=2, page_size=2)
    assert page.total == 3 and len(page.items) == 1
