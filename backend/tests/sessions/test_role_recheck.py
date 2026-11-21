"""I ruoli della dashboard vengono riverificati su Keycloak, non restano quelli del login."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from app.modules.identity import IdentityError
from app.modules.sessions.models import UserSession


class RolesSource:
    def __init__(self) -> None:
        self.roles: frozenset[str] | None = frozenset({"iam-admin"})
        self.down = False
        self.calls = 0

    async def current_roles(self, username: str) -> frozenset[str] | None:
        self.calls += 1
        if self.down:
            raise IdentityError("Keycloak non raggiungibile")
        return self.roles


@pytest.fixture
def roles(api) -> RolesSource:
    source = RolesSource()
    api._transport.app.state.identity = source
    return source


async def age_sessions(session, minutes: int) -> None:
    old = datetime.now(UTC) - timedelta(minutes=minutes)
    await session.execute(update(UserSession).values(roles_checked_at=old, created_at=old))


async def test_recent_session_is_not_rechecked(api, session, login_as, roles) -> None:
    await login_as(api, "iam-admin")
    await age_sessions(session, 1)
    assert (await api.get("/api/auth/me")).status_code == 200
    assert roles.calls == 0


async def test_removed_role_takes_effect(api, session, login_as, roles) -> None:
    await login_as(api, "iam-admin")
    await age_sessions(session, 6)
    roles.roles = frozenset({"default-roles-argo"})
    assert (await api.get("/api/auth/me")).json()["roles"] == []
    assert (await api.get("/api/employees")).status_code == 403


async def test_disabled_user_loses_the_session(api, session, login_as, roles) -> None:
    await login_as(api, "iam-admin")
    await age_sessions(session, 6)
    roles.roles = None
    assert (await api.get("/api/auth/me")).status_code == 401
    roles.roles = frozenset({"iam-admin"})
    assert (await api.get("/api/auth/me")).status_code == 401  # revocata, non torna


async def test_keycloak_down_keeps_known_roles(api, session, login_as, roles) -> None:
    await login_as(api, "iam-owner")
    await age_sessions(session, 6)
    roles.down = True
    assert (await api.get("/api/auth/me")).json()["roles"] == ["iam-owner"]
