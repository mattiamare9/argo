from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules import audit
from app.modules.employees import repository
from app.modules.employees.models import Employee
from app.modules.employees.schemas import (
    AppliedChange,
    ChangeKind,
    EmployeeOut,
    EmployeePage,
    EmployeeRecord,
    PlannedChange,
)

MAX_PAGE_SIZE = 100


def key_of(employee_id: str) -> str:
    return employee_id.strip().lower()


def _profile(record: EmployeeRecord) -> tuple[str, str, str]:
    return record.email.lower(), record.first_name, record.last_name


async def plan_changes(session: AsyncSession, records: list[EmployeeRecord]) -> list[PlannedChange]:
    """Confronta la fonte con l'anagrafica. Non modifica nulla."""
    existing = await repository.get_by_keys(session, (key_of(r.employee_id) for r in records))
    plan = []
    for record in records:
        current = existing.get(key_of(record.employee_id))
        if current is None:
            plan.append(PlannedChange(record, ChangeKind.CREATED, profile_changed=False))
            continue
        profile_changed = _profile(record) != (current.email, current.first_name, current.last_name)
        if current.status == "ACTIVE" and record.status == "INACTIVE":
            kind = ChangeKind.DEACTIVATED
        elif current.status == "INACTIVE" and record.status == "ACTIVE":
            kind = ChangeKind.REACTIVATED
        elif profile_changed:
            kind = ChangeKind.UPDATED
        else:
            kind = ChangeKind.UNCHANGED
        plan.append(PlannedChange(record, kind, profile_changed))
    return plan


async def find_email_conflicts(session: AsyncSession, records: list[EmployeeRecord]) -> list[str]:
    """Email della fonte già usate da dipendenti che la fonte non elenca."""
    return await repository.emails_held_outside(
        session,
        (r.email.lower() for r in records),
        (key_of(r.employee_id) for r in records),
    )


async def count_missing(session: AsyncSession, records: list[EmployeeRecord]) -> int:
    """Dipendenti noti ad Argo ma assenti dalla fonte. Non vengono mai disattivati."""
    return await repository.count_not_in(session, (key_of(r.employee_id) for r in records))


async def apply_changes(
    session: AsyncSession, plan: list[PlannedChange], *, source: str, actor: str
) -> list[AppliedChange]:
    """Applica il piano nella transazione del chiamante (nessun commit)."""
    existing = await repository.get_by_keys(session, (key_of(c.record.employee_id) for c in plan))
    now = datetime.now(UTC)
    applied = []
    for change in plan:
        if change.kind is ChangeKind.UNCHANGED:
            continue
        record = change.record
        email, first_name, last_name = _profile(record)
        employee = existing.get(key_of(record.employee_id))
        if employee is None:
            employee = Employee(
                employee_id=record.employee_id.strip(),
                employee_key=key_of(record.employee_id),
                status=record.status,
                source=source,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            await repository.add(session, employee)
        else:
            employee.email, employee.first_name, employee.last_name = email, first_name, last_name
            employee.updated_at = now
            if employee.status != record.status:
                employee.status = record.status
                employee.status_changed_at = now
        await audit.record(
            session,
            actor=actor,
            action=f"employee.{change.kind.value}",
            outcome="success",
            target_type="employee",
            target_id=employee.employee_id,
            details={"status": record.status, "profile_changed": change.profile_changed},
        )
        applied.append(
            AppliedChange(employee.employee_id, change.kind, record.status, change.profile_changed)
        )
    await session.flush()
    return applied


async def list_employees(
    session: AsyncSession,
    *,
    search: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> EmployeePage:
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
    page = max(page, 1)
    rows, total = await repository.page(
        session, search=search, status=status, offset=(page - 1) * page_size, limit=page_size
    )
    return EmployeePage(
        items=[EmployeeOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
