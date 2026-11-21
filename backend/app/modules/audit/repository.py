from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditEvent


async def add(session: AsyncSession, event: AuditEvent) -> AuditEvent:
    session.add(event)
    await session.flush()
    return event
