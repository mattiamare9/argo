import base64
import json
import time
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi import Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.session import get_db
from app.main import create_app
from app.modules.audit.models import AuditEvent
from app.modules.sessions import require_role, revoke_for_subject
from app.modules.sessions.models import UserSession

ISSUER = "http://kc.test/realms/argo"


def fake_jwt(claims: dict) -> str:
    def enc(obj: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    return f"{enc({'alg': 'none'})}.{enc(claims)}.firma"


class FakeIdp:
    def __init__(self) -> None:
        self.nonce = ""
        self.roles = ["iam-admin", "default-roles-argo"]
        self.unreachable = False
        self.token_form: dict[str, list[str]] = {}

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/.well-known/openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "authorization_endpoint": f"{ISSUER}/protocol/openid-connect/auth",
                    "token_endpoint": f"{ISSUER}/protocol/openid-connect/token",
                    "end_session_endpoint": f"{ISSUER}/protocol/openid-connect/logout",
                },
            )
        if self.unreachable:
            raise httpx.ConnectError("down")
        self.token_form = parse_qs(request.content.decode())
        now = int(time.time())
        id_token = {
            "iss": ISSUER,
            "aud": "argo-dashboard",
            "exp": now + 300,
            "nonce": self.nonce,
            "sub": "kc-sub-1",
            "preferred_username": "admin1",
            "name": "Mario Rossi",
            "email": "mario@example.com",
        }
        access = {"iss": ISSUER, "sub": "kc-sub-1", "realm_access": {"roles": self.roles}}
        return httpx.Response(
            200, json={"id_token": fake_jwt(id_token), "access_token": fake_jwt(access)}
        )


@pytest.fixture
def idp() -> FakeIdp:
    return FakeIdp()


@pytest.fixture
async def app(idp: FakeIdp, session: AsyncSession, migrated_database: str):
    settings = Settings(
        database_url=migrated_database,
        keycloak_url="http://kc.test",
        oidc_client_secret="s3cret",
        public_url="http://testserver",
    )
    http = httpx.AsyncClient(transport=httpx.MockTransport(idp.handler))
    app = create_app(settings, http=http)
    app.dependency_overrides[get_db] = lambda: session

    @app.get("/api/test-admin", dependencies=[Depends(require_role("iam-admin"))])
    async def admin_only() -> dict:
        return {"ok": True}

    yield app
    await http.aclose()
    await app.state.engine.dispose()


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


async def start_login(client, idp: FakeIdp, next_path: str = "/") -> str:
    response = await client.get("/api/auth/login", params={"next": next_path})
    assert response.status_code == 302
    query = parse_qs(urlparse(response.headers["location"]).query)
    idp.nonce = query["nonce"][0]
    return query["state"][0]


async def log_in(client, idp: FakeIdp, next_path: str = "/") -> httpx.Response:
    state = await start_login(client, idp, next_path)
    return await client.get("/api/auth/callback", params={"code": "abc", "state": state})


async def test_login_redirects_to_idp_with_pkce(client, idp) -> None:
    response = await client.get("/api/auth/login")
    location = urlparse(response.headers["location"])
    query = parse_qs(location.query)
    assert location.geturl().startswith(f"{ISSUER}/protocol/openid-connect/auth")
    assert query["code_challenge_method"] == ["S256"]
    assert query["client_id"] == ["argo-dashboard"]
    assert query["redirect_uri"] == ["http://testserver/api/auth/callback"]
    assert response.cookies["argo_login"] == query["state"][0]


async def test_full_login_creates_session(client, idp, session) -> None:
    response = await log_in(client, idp, "/dipendenti")
    assert response.status_code == 302
    assert response.headers["location"] == "/dipendenti"
    assert "httponly" in response.headers["set-cookie"].lower()
    assert idp.token_form["code_verifier"]  # PKCE inviato al token endpoint

    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json() == {
        "username": "admin1",
        "display_name": "Mario Rossi",
        "email": "mario@example.com",
        "roles": ["iam-admin"],
    }
    actions = (await session.scalars(select(AuditEvent.action))).all()
    assert "auth.login" in actions


async def test_callback_with_wrong_state_is_rejected(client, idp) -> None:
    await start_login(client, idp)
    response = await client.get("/api/auth/callback", params={"code": "abc", "state": "altro"})
    assert response.status_code == 400
    assert "argo_session" not in response.cookies


async def test_callback_with_wrong_nonce_is_rejected(client, idp) -> None:
    state = await start_login(client, idp)
    idp.nonce = "manomesso"
    response = await client.get("/api/auth/callback", params={"code": "abc", "state": state})
    assert response.status_code == 400


async def test_idp_unreachable_during_callback_returns_502(client, idp) -> None:
    state = await start_login(client, idp)
    idp.unreachable = True
    response = await client.get("/api/auth/callback", params={"code": "abc", "state": state})
    assert response.status_code == 502
    assert "argo_session" not in response.cookies


async def test_open_redirect_is_blocked(client, idp) -> None:
    response = await log_in(client, idp, "//evil.example/rubare")
    assert response.headers["location"] == "/"


async def test_logout_requires_csrf_header(client, idp) -> None:
    await log_in(client, idp)
    response = await client.post("/api/auth/logout")
    assert response.status_code == 403


async def test_logout_revokes_session(client, idp) -> None:
    await log_in(client, idp)
    response = await client.post("/api/auth/logout", headers={"X-Argo-CSRF": "1"})
    assert response.status_code == 200
    assert response.json()["logout_url"].startswith(f"{ISSUER}/protocol/openid-connect/logout")
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_idle_session_expires(client, idp, session) -> None:
    await log_in(client, idp)
    old = datetime.now(UTC) - timedelta(minutes=31)
    await session.execute(update(UserSession).values(last_seen_at=old))
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_role_is_required_for_protected_routes(client, idp) -> None:
    idp.roles = ["default-roles-argo"]  # dipendente qualunque, nessun ruolo iam-*
    await log_in(client, idp)
    assert (await client.get("/api/auth/me")).json()["roles"] == []
    assert (await client.get("/api/test-admin")).status_code == 403


async def test_admin_reaches_protected_route(client, idp) -> None:
    await log_in(client, idp)
    assert (await client.get("/api/test-admin")).status_code == 200


async def test_anonymous_gets_401(client) -> None:
    assert (await client.get("/api/test-admin")).status_code == 401


async def test_revoke_for_subject_ends_all_sessions(client, idp, session) -> None:
    await log_in(client, idp)
    assert await revoke_for_subject(session, "kc-sub-1") == 1
    assert (await client.get("/api/auth/me")).status_code == 401


def test_issuer_uses_public_keycloak_url_when_set() -> None:
    internal = Settings(
        database_url="postgresql+asyncpg://x/y", keycloak_url="http://keycloak:8080"
    )
    assert internal.oidc_issuer == "http://keycloak:8080/realms/argo"
    public = Settings(
        database_url="postgresql+asyncpg://x/y",
        keycloak_url="http://keycloak:8080",
        keycloak_public_url="https://accesso.azienda.it",
    )
    assert public.oidc_issuer == "https://accesso.azienda.it/realms/argo"
