import json

import httpx
import pytest

from app.modules.identity import IdentityError, IdentityUser, UserNotFound
from app.modules.identity.keycloak_adapter import KeycloakIdentityProvider

BASE = "http://kc.test"
USERS = f"{BASE}/admin/realms/argo/users"


class FakeKeycloak:
    """Keycloak minimale in memoria, con le risposte verificate su 26.8.2."""

    def __init__(self) -> None:
        self.users: dict[str, dict] = {}
        self.token_requests = 0
        self.requests: list[httpx.Request] = []
        self.fail_with: int | None = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path.endswith("/protocol/openid-connect/token"):
            self.token_requests += 1
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 300})
        if self.fail_with:
            return httpx.Response(self.fail_with)
        assert request.headers["authorization"] == "Bearer tok"
        if path == "/admin/realms/argo/users" and request.method == "GET":
            name = request.url.params["username"].lower()
            return httpx.Response(
                200, json=[u for u in self.users.values() if u["username"] == name]
            )
        if path == "/admin/realms/argo/users" and request.method == "POST":
            body = json.loads(request.content)
            uid = f"id-{len(self.users)}"
            self.users[uid] = {**body, "id": uid, "username": body["username"].lower()}
            return httpx.Response(201)
        if path == "/admin/realms/argo/roles/iam-admin":
            return httpx.Response(200, json={"id": "r1", "name": "iam-admin"})
        uid = path.split("/")[5]
        if uid not in self.users:
            return httpx.Response(404)
        if request.method == "PUT" and path.endswith(uid):
            self.users[uid].update(json.loads(request.content))
        return httpx.Response(204)


@pytest.fixture
def kc() -> FakeKeycloak:
    return FakeKeycloak()


@pytest.fixture
def provider(kc: FakeKeycloak) -> KeycloakIdentityProvider:
    http = httpx.AsyncClient(transport=httpx.MockTransport(kc.handler))
    return KeycloakIdentityProvider(BASE, "argo", "argo-backend", "secret", http)


MARIO = IdentityUser(
    employee_id="E001", email="mario@example.com", first_name="Mario", last_name="Rossi"
)


async def test_ensure_user_creates_missing_user(provider, kc) -> None:
    await provider.ensure_user(MARIO)
    (user,) = kc.users.values()
    assert user["username"] == "e001"
    assert user["email"] == "mario@example.com"
    assert user["enabled"] is True


async def test_ensure_user_updates_existing_user_without_touching_enabled(provider, kc) -> None:
    await provider.ensure_user(MARIO)
    await provider.set_enabled("E001", False)
    await provider.ensure_user(
        IdentityUser(
            employee_id="E001", email="nuova@example.com", first_name="Mario", last_name="Rossi"
        )
    )
    (user,) = kc.users.values()
    assert user["email"] == "nuova@example.com"
    assert user["enabled"] is False  # l'aggiornamento anagrafico non riattiva nessuno
    assert len(kc.users) == 1


async def test_token_is_reused(provider, kc) -> None:
    await provider.ensure_user(MARIO)
    await provider.set_enabled("E001", False)
    assert kc.token_requests == 1


async def test_set_enabled_on_missing_user_raises(provider) -> None:
    with pytest.raises(UserNotFound):
        await provider.set_enabled("E999", False)


async def test_logout_calls_keycloak(provider, kc) -> None:
    await provider.ensure_user(MARIO)
    await provider.logout("E001")
    assert kc.requests[-1].method == "POST"
    assert kc.requests[-1].url.path.endswith("/logout")


async def test_send_enrollment_requests_passkey_registration(provider, kc) -> None:
    await provider.ensure_user(MARIO)
    await provider.send_enrollment("E001")
    last = kc.requests[-1]
    assert last.url.path.endswith("/execute-actions-email")
    assert json.loads(last.content) == ["webauthn-register-passwordless"]


async def test_grant_role_maps_realm_role(provider, kc) -> None:
    await provider.ensure_user(MARIO)
    await provider.grant_role("E001", "iam-admin")
    last = kc.requests[-1]
    assert last.url.path.endswith("/role-mappings/realm")
    assert json.loads(last.content) == [{"id": "r1", "name": "iam-admin"}]


async def test_server_error_raises_identity_error(provider, kc) -> None:
    kc.fail_with = 503
    with pytest.raises(IdentityError):
        await provider.logout("E001")
