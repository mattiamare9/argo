from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit import repository
from app.modules.audit.models import AuditEvent


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
