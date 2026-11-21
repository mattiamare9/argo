from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sessions.models import LoginAttempt, UserSession


async def add(session: AsyncSession, obj: LoginAttempt | UserSession) -> None:
    session.add(obj)
    await session.flush()


async def pop_login_attempt(session: AsyncSession, state: str) -> LoginAttempt | None:
    """Monouso: il tentativo viene cancellato appena letto."""
    attempt = await session.get(LoginAttempt, state)
    if attempt is not None:
        await session.delete(attempt)
        await session.flush()
    return attempt


async def delete_login_attempts_before(session: AsyncSession, cutoff: datetime) -> None:
    await session.execute(delete(LoginAttempt).where(LoginAttempt.created_at < cutoff))


async def get_by_token_hash(session: AsyncSession, token_hash: str) -> UserSession | None:
    return await session.scalar(select(UserSession).where(UserSession.token_hash == token_hash))


async def revoke_username(session: AsyncSession, username: str, now: datetime) -> int:
    result = await session.execute(
        update(UserSession)
        .where(UserSession.username == username, UserSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    return result.rowcount


async def revoke_subject(session: AsyncSession, subject: str, now: datetime) -> int:
    result = await session.execute(
        update(UserSession)
        .where(UserSession.subject == subject, UserSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    return result.rowcount
