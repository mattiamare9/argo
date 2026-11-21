"""Comandi di amministrazione. Uso: uv run python -m app.cli <comando> --help"""

import argparse
import asyncio

import httpx

from app.core.config import get_settings
from app.modules.identity import IdentityProvider, IdentityUser, build_identity_provider


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


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    boot = commands.add_parser("bootstrap-admin", help="crea il primo amministratore")
    boot.add_argument("--employee-id", required=True)
    boot.add_argument("--email", required=True)
    boot.add_argument("--first-name", required=True)
    boot.add_argument("--last-name", required=True)
    args = parser.parse_args()
    if args.command == "bootstrap-admin":
        asyncio.run(_run_bootstrap(args))


if __name__ == "__main__":
    main()
