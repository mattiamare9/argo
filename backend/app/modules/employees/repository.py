from collections.abc import Iterable

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.employees.models import Employee


async def get_by_keys(session: AsyncSession, keys: Iterable[str]) -> dict[str, Employee]:
    rows = await session.scalars(select(Employee).where(Employee.employee_key.in_(list(keys))))
    return {e.employee_key: e for e in rows}


async def emails_held_outside(
    session: AsyncSession, emails: Iterable[str], keys: Iterable[str]
) -> list[str]:
    """Email già usate da dipendenti che non compaiono tra `keys`."""
    rows = await session.scalars(
        select(Employee.email).where(
            Employee.email.in_(list(emails)), Employee.employee_key.not_in(list(keys))
        )
    )
    return sorted(rows)


async def count_not_in(session: AsyncSession, keys: Iterable[str]) -> int:
    query = select(func.count()).where(Employee.employee_key.not_in(list(keys)))
    return await session.scalar(query.select_from(Employee)) or 0


async def add(session: AsyncSession, employee: Employee) -> None:
    session.add(employee)


async def page(
    session: AsyncSession,
    *,
    search: str | None,
    status: str | None,
    offset: int,
    limit: int,
) -> tuple[list[Employee], int]:
    query = select(Employee)
    if status:
        query = query.where(Employee.status == status)
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            or_(
                Employee.employee_key.like(pattern),
                Employee.email.like(pattern),
                func.lower(Employee.first_name + " " + Employee.last_name).like(pattern),
            )
        )
    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = await session.scalars(
        query.order_by(Employee.last_name, Employee.first_name, Employee.employee_key)
        .offset(offset)
        .limit(limit)
    )
    return list(rows), total
