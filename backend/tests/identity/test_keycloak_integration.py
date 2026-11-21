"""Ciclo di vita completo contro il Keycloak reale del profilo `idp`."""

import secrets

import httpx
import pytest

from app.core.config import Settings
from app.modules.identity import IdentityUser, UserNotFound, build_identity_provider


@pytest.fixture
async def provider(keycloak_url: str):
    settings = Settings(keycloak_url=keycloak_url)  # segreti e DB da backend/.env
    async with httpx.AsyncClient(timeout=10) as http:
        yield build_identity_provider(settings, http)


async def test_full_lifecycle_against_keycloak(provider) -> None:
    employee_id = f"TEST-{secrets.token_hex(4)}"
    user = IdentityUser(employee_id, f"{employee_id.lower()}@example.com", "Prova", "Integrazione")

    await provider.ensure_user(user)
    await provider.ensure_user(user)  # idempotente
    await provider.grant_role(employee_id, "iam-owner")
    await provider.send_enrollment(employee_id)
    await provider.set_enabled(employee_id, False)
    await provider.logout(employee_id)
    await provider.set_enabled(employee_id, True)


async def test_missing_user_is_reported(provider) -> None:
    with pytest.raises(UserNotFound):
        await provider.set_enabled("NON-ESISTE-MAI", False)
