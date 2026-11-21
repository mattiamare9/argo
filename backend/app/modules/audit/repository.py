from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditEvent


async def add(session: AsyncSession, event: AuditEvent) -> AuditEvent:
    session.add(event)
    await session.flush()
    return event


async def page(
    session: AsyncSession,
    *,
    search: str | None,
    outcome: str | None,
    offset: int,
    limit: int,
) -> tuple[list[AuditEvent], int]:
    query = select(AuditEvent)
    if outcome:
        query = query.where(AuditEvent.outcome == outcome)
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(AuditEvent.actor).like(pattern),
                func.lower(AuditEvent.action).like(pattern),
                func.lower(AuditEvent.target_id).like(pattern),
            )
        )
    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = await session.scalars(
        query.order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(rows), total
