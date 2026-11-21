"""Handler dei job di provisioning, eseguiti dal worker."""

import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.modules import applications, audit, employees, sessions
from app.modules.connectors import AppAccount, build_connector
from app.modules.identity import IdentityProvider, IdentityUser, UserNotFound
from app.modules.jobs import Handler, ManualActionRequired

logger = logging.getLogger(__name__)


def build_handlers(
    identity: IdentityProvider,
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
    http: httpx.AsyncClient,
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

    def missing_account(employee_id: str) -> ManualActionRequired:
        # Un account non trovato non è un account chiuso: può esistere con un altro nome.
        return ManualActionRequired(
            f"Nessun account aziendale trovato per {employee_id}: verifica in Keycloak che non "
            "esista con un altro nome utente, poi premi Fatto."
        )

    async def disable(payload: dict[str, Any]) -> None:
        try:
            await identity.set_enabled(payload["employee_id"], False)
        except UserNotFound as exc:
            raise missing_account(payload["employee_id"]) from exc

    async def logout(payload: dict[str, Any]) -> None:
        try:
            await identity.logout(payload["employee_id"])
        except UserNotFound as exc:
            raise missing_account(payload["employee_id"]) from exc

    async def revoke_dashboard(payload: dict[str, Any]) -> None:
        async with sessionmaker() as db:
            await sessions.revoke_for_username(db, payload["employee_id"])
            await db.commit()

    async def run_on_app(payload: dict[str, Any], action: str) -> None:
        async with sessionmaker() as db:
            app = await applications.get_application(db, uuid.UUID(payload["app_id"]))
        if app is None or not app.enabled:
            if action == "deprovision":  # l'account può essere ancora aperto
                raise ManualActionRequired(
                    f"L'applicazione «{payload.get('label', payload['app_id'])}» non è più "
                    f"gestita da Argo: verifica a mano che l'account di {payload['email']} "
                    "sia chiuso, poi premi Fatto."
                )
            logger.info("applicazione %s eliminata o sospesa: nulla da creare", payload["app_id"])
            return
        connector = build_connector(app, settings, http)
        account = AppAccount(
            *(payload[k] for k in ("employee_id", "email", "first_name", "last_name"))
        )
        await getattr(connector, action)(account)

    async def app_provision(payload: dict[str, Any]) -> None:
        await run_on_app(payload, "provision")

    async def app_deprovision(payload: dict[str, Any]) -> None:
        await run_on_app(payload, "deprovision")

    plain = {
        "app.provision": app_provision,
        "app.deprovision": app_deprovision,
        "identity.provision": provision,
        "identity.update_profile": update_profile,
        "identity.disable": disable,
        "identity.logout": logout,
        "dashboard.revoke_sessions": revoke_dashboard,
    }
    return {
        kind: _audited(kind, _current_only(kind, fn, sessionmaker), sessionmaker)
        for kind, fn in plain.items()
    }


# Passi che hanno senso solo se il dipendente è ancora nello stato che li ha generati.
REQUIRES_STATUS = {
    "identity.provision": "ACTIVE",
    "identity.update_profile": "ACTIVE",
    "app.provision": "ACTIVE",
    "identity.disable": "INACTIVE",
    "identity.logout": "INACTIVE",
    "dashboard.revoke_sessions": "INACTIVE",
    "app.deprovision": "INACTIVE",
}


def _current_only(
    kind: str,
    fn: Callable[[dict[str, Any]], Awaitable[None]],
    sessionmaker: async_sessionmaker[AsyncSession],
) -> Callable[[dict[str, Any]], Awaitable[None]]:
    """Un job in ritardo (retry) non deve annullare un cambio più recente.

    Es. un invito ritentato dopo che il dipendente è uscito, o una disattivazione ritentata
    dopo una riassunzione: il passo viene saltato e il run più recente fa testo.
    """

    async def run(payload: dict[str, Any]) -> None:
        async with sessionmaker() as db:
            status = await employees.current_status(db, payload["employee_id"])
        if status is not None and status != REQUIRES_STATUS[kind]:
            logger.info(
                "%s per %s saltato: il dipendente ora è %s",
                kind,
                payload["employee_id"],
                status,
            )
            return
        await fn(payload)

    return run


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
