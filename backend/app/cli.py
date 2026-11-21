"""Comandi di amministrazione. Uso: uv run python -m app.cli <comando> --help"""

import argparse
import asyncio

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import get_settings
from app.db.session import create_engine
from app.modules.employees import list_employees
from app.modules.identity import (
    IdentityError,
    IdentityProvider,
    IdentityUser,
    build_identity_provider,
)
from app.modules.synchronization import create_agent


async def bootstrap_admin(provider: IdentityProvider, user: IdentityUser) -> None:
    """Primo amministratore: crea l'utente, assegna iam-admin, invia l'email per la passkey."""
    await provider.ensure_user(user)
    await provider.grant_role(user.employee_id, "iam-admin")
    await provider.send_enrollment(user.employee_id)


async def _run_bootstrap(args: argparse.Namespace) -> None:
    async with httpx.AsyncClient(timeout=10) as http:
        provider = build_identity_provider(get_settings(), http)
        user = IdentityUser(args.employee_id, args.email, args.first_name, args.last_name)
        await bootstrap_admin(provider, user)
    print(f"Creato {args.employee_id}: email di registrazione passkey inviata a {args.email}")


async def _run_create_agent(args: argparse.Namespace) -> None:
    engine = create_engine(get_settings().database_url)
    async with async_sessionmaker(engine)() as db:
        key = await create_agent(db, args.name)
    await engine.dispose()
    print(f"Agent {args.name} creato. Chiave API (mostrata solo ora):\n{key}")


async def send_invites(provider: IdentityProvider, employee_ids: list[str]) -> list[str]:
    """Invia l'invito passkey a ciascuno; restituisce chi non è stato raggiunto."""
    failed = []
    for employee_id in employee_ids:
        try:
            await provider.send_enrollment(employee_id)
        except IdentityError:
            failed.append(employee_id)
    return failed


async def _run_send_invites(args: argparse.Namespace) -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    async with async_sessionmaker(engine)() as db:
        page = await list_employees(db, status="ACTIVE", page_size=100)
    await engine.dispose()
    ids = [e.employee_id for e in page.items]
    async with httpx.AsyncClient(timeout=10) as http:
        failed = await send_invites(build_identity_provider(settings, http), ids)
    print(f"Inviti inviati: {len(ids) - len(failed)} su {len(ids)}")
    if failed:
        print("Non raggiunti (account mancante o Keycloak in errore):", ", ".join(failed))


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    boot = commands.add_parser("bootstrap-admin", help="crea il primo amministratore")
    boot.add_argument("--employee-id", required=True)
    boot.add_argument("--email", required=True)
    boot.add_argument("--first-name", required=True)
    boot.add_argument("--last-name", required=True)
    agent = commands.add_parser("create-agent", help="crea un Sync Agent e la sua chiave API")
    agent.add_argument("--name", required=True)
    commands.add_parser("send-invites", help="invia l'invito passkey a tutti i dipendenti attivi")
    args = parser.parse_args()
    if args.command == "bootstrap-admin":
        asyncio.run(_run_bootstrap(args))
    elif args.command == "create-agent":
        asyncio.run(_run_create_agent(args))
    elif args.command == "send-invites":
        asyncio.run(_run_send_invites(args))


if __name__ == "__main__":
    main()
