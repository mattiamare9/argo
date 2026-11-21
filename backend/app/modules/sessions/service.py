import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules import audit
from app.modules.sessions import repository
from app.modules.sessions.models import LoginAttempt, UserSession
from app.modules.sessions.oidc import (
    OidcClient,
    OidcError,
    decode_claims,
    pkce_pair,
    validate_id_token,
)

IDLE_TIMEOUT = timedelta(minutes=30)  # allineato a ssoSessionIdleTimeout del realm
ABSOLUTE_TIMEOUT = timedelta(hours=10)  # allineato a ssoSessionMaxLifespan
LOGIN_ATTEMPT_TTL = timedelta(minutes=10)
TOUCH_INTERVAL = timedelta(minutes=1)
DASHBOARD_ROLES = frozenset({"iam-admin", "iam-owner"})


class LoginRejected(Exception):
    """Il callback non corrisponde a un login avviato da questo browser."""


@dataclass(frozen=True)
class CurrentUser:
    subject: str
    username: str
    display_name: str
    email: str | None
    roles: frozenset[str]


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def safe_next(path: str | None) -> str:
    """Solo percorsi interni: blocca open redirect verso altri domini."""
    if not path or not path.startswith("/") or path.startswith("//") or "\\" in path:
        return "/"
    return path


async def start_login(db: AsyncSession, oidc: OidcClient, next_path: str | None) -> tuple[str, str]:
    """Restituisce (URL dell'identity provider, state da legare al browser)."""
    now = datetime.now(UTC)
    await repository.delete_login_attempts_before(db, now - LOGIN_ATTEMPT_TTL)
    state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    verifier, challenge = pkce_pair()
    url = await oidc.authorization_url(state, nonce, challenge)
    attempt = LoginAttempt(
        state=state, nonce=nonce, code_verifier=verifier, next_path=safe_next(next_path)
    )
    await repository.add(db, attempt)
    await db.commit()
    return url, state


async def complete_login(
    db: AsyncSession, oidc: OidcClient, *, state: str, code: str, browser_state: str | None
) -> tuple[str, str]:
    """Restituisce (token di sessione per il cookie, percorso a cui tornare).

    Solleva LoginRejected (richiesta non valida) o OidcError (identity provider).
    """
    if not browser_state or not secrets.compare_digest(state, browser_state):
        await _audit_failure(db, "state non corrispondente al browser")
        raise LoginRejected("login non avviato da questo browser")
    attempt = await repository.pop_login_attempt(db, state)
    if attempt is None or attempt.created_at < datetime.now(UTC) - LOGIN_ATTEMPT_TTL:
        await _audit_failure(db, "tentativo di login scaduto o già usato")
        raise LoginRejected("login scaduto, riprova")

    tokens = await oidc.exchange_code(code, attempt.code_verifier)
    id_claims = decode_claims(tokens["id_token"])
    try:
        validate_id_token(id_claims, oidc.config, attempt.nonce)
    except OidcError as exc:
        await _audit_failure(db, str(exc))
        raise LoginRejected(str(exc)) from exc
    access_claims = decode_claims(tokens["access_token"])
    roles = DASHBOARD_ROLES & set(access_claims.get("realm_access", {}).get("roles", []))

    now = datetime.now(UTC)
    token = secrets.token_urlsafe(32)
    username = id_claims.get("preferred_username", id_claims["sub"])
    user_session = UserSession(
        token_hash=hash_token(token),
        subject=id_claims["sub"],
        username=username,
        display_name=id_claims.get("name") or username,
        email=id_claims.get("email"),
        roles=sorted(roles),
        last_seen_at=now,
        expires_at=now + ABSOLUTE_TIMEOUT,
    )
    await repository.add(db, user_session)
    await audit.record(
        db,
        actor=f"user:{username}",
        action="auth.login",
        outcome="success",
        target_type="user",
        target_id=id_claims["sub"],
        details={"roles": sorted(roles)},
    )
    await db.commit()
    return token, attempt.next_path


async def get_current(db: AsyncSession, token: str | None) -> CurrentUser | None:
    if not token:
        return None
    user_session = await repository.get_by_token_hash(db, hash_token(token))
    now = datetime.now(UTC)
    if (
        user_session is None
        or user_session.revoked_at is not None
        or user_session.expires_at <= now
        or user_session.last_seen_at <= now - IDLE_TIMEOUT
    ):
        return None
    if user_session.last_seen_at <= now - TOUCH_INTERVAL:
        user_session.last_seen_at = now
        await db.commit()
    return CurrentUser(
        subject=user_session.subject,
        username=user_session.username,
        display_name=user_session.display_name,
        email=user_session.email,
        roles=frozenset(user_session.roles),
    )


async def logout(db: AsyncSession, token: str, user: CurrentUser) -> None:
    user_session = await repository.get_by_token_hash(db, hash_token(token))
    if user_session is not None and user_session.revoked_at is None:
        user_session.revoked_at = datetime.now(UTC)
    await audit.record(
        db,
        actor=f"user:{user.username}",
        action="auth.logout",
        outcome="success",
        target_type="user",
        target_id=user.subject,
    )
    await db.commit()


async def revoke_for_subject(db: AsyncSession, subject: str) -> int:
    """Revoca tutte le sessioni di un utente (es. offboarding). Commit del chiamante."""
    return await repository.revoke_subject(db, subject, datetime.now(UTC))


async def revoke_for_username(db: AsyncSession, username: str) -> int:
    """Come revoke_for_subject, per username Keycloak (= employee_id, ADR-021)."""
    return await repository.revoke_username(db, username.lower(), datetime.now(UTC))


async def _audit_failure(db: AsyncSession, reason: str) -> None:
    await audit.record(
        db, actor="anonymous", action="auth.login", outcome="failure", details={"reason": reason}
    )
    await db.commit()
