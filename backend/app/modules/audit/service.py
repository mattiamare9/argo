from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit import repository
from app.modules.audit.models import AuditEvent
from app.modules.audit.schemas import AuditEventOut, AuditPage


async def record(
    session: AsyncSession,
    *,
    actor: str,
    action: str,
    outcome: Literal["success", "failure"],
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    """Registra un evento nella transazione del chiamante, senza commit.

    Così l'evento di audit e l'operazione che descrive vengono salvati insieme o per niente.
    `details` non deve mai contenere password, token o segreti.
    """
    event = AuditEvent(
        actor=actor,
        action=action,
        outcome=outcome,
        target_type=target_type,
        target_id=target_id,
        details=details or {},
    )
    return await repository.add(session, event)


MAX_PAGE_SIZE = 100


async def list_events(
    session: AsyncSession,
    *,
    search: str | None = None,
    outcome: Literal["success", "failure"] | None = None,
    page: int = 1,
    page_size: int = 50,
) -> AuditPage:
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
    page = max(page, 1)
    rows, total = await repository.page(
        session, search=search, outcome=outcome, offset=(page - 1) * page_size, limit=page_size
    )
    return AuditPage(
        items=[AuditEventOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
