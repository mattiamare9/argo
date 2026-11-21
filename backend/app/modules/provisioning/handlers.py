"""Handler dei job di provisioning, eseguiti dal worker."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules import audit, sessions
from app.modules.identity import IdentityProvider, IdentityUser, UserNotFound
from app.modules.jobs import Handler

logger = logging.getLogger(__name__)


def build_handlers(
    identity: IdentityProvider, sessionmaker: async_sessionmaker[AsyncSession]
) -> dict[str, Handler]:
    def user_of(payload: dict[str, Any]) -> IdentityUser:
        return IdentityUser(
            payload["employee_id"], payload["email"], payload["first_name"], payload["last_name"]
        )

    async def provision(payload: dict[str, Any]) -> None:
        user = user_of(payload)
        await identity.ensure_user(user)
        await identity.set_enabled(user.employee_id, True)
        await identity.send_enrollment(user.employee_id)

    async def update_profile(payload: dict[str, Any]) -> None:
        await identity.ensure_user(user_of(payload))

    async def disable(payload: dict[str, Any]) -> None:
        try:
            await identity.set_enabled(payload["employee_id"], False)
        except UserNotFound:
            logger.info("nessun account per %s: nulla da disattivare", payload["employee_id"])

    async def logout(payload: dict[str, Any]) -> None:
        try:
            await identity.logout(payload["employee_id"])
        except UserNotFound:
            logger.info("nessun account per %s: nessuna sessione", payload["employee_id"])

    async def revoke_dashboard(payload: dict[str, Any]) -> None:
        async with sessionmaker() as db:
            await sessions.revoke_for_username(db, payload["employee_id"])
            await db.commit()

    plain = {
        "identity.provision": provision,
        "identity.update_profile": update_profile,
        "identity.disable": disable,
        "identity.logout": logout,
        "dashboard.revoke_sessions": revoke_dashboard,
    }
    return {kind: _audited(kind, fn, sessionmaker) for kind, fn in plain.items()}


def _audited(
    kind: str,
    fn: Callable[[dict[str, Any]], Awaitable[None]],
    sessionmaker: async_sessionmaker[AsyncSession],
) -> Handler:
    """Registra nell'audit l'esito di ogni tentativo (specifica §13.3)."""

    async def run(payload: dict[str, Any]) -> None:
        outcome, details = "success", {}
        try:
            await fn(payload)
        except Exception as exc:
            outcome, details = "failure", {"error": f"{type(exc).__name__}: {exc}"[:500]}
            raise
        finally:
            async with sessionmaker() as db:
                await audit.record(
                    db,
                    actor="worker",
                    action=kind,
                    outcome=outcome,
                    target_type="employee",
                    target_id=payload.get("employee_id"),
                    details=details,
                )
                await db.commit()

    return run
