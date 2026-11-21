import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.synchronization.models import SyncAgent, SyncSnapshot


async def add(session: AsyncSession, obj: SyncAgent | SyncSnapshot) -> None:
    session.add(obj)
    await session.flush()


async def agent_by_key_hash(session: AsyncSession, key_hash: str) -> SyncAgent | None:
    return await session.scalar(
        select(SyncAgent).where(SyncAgent.key_hash == key_hash, SyncAgent.revoked_at.is_(None))
    )


async def agent_by_name(session: AsyncSession, name: str) -> SyncAgent | None:
    return await session.scalar(
        select(SyncAgent).where(SyncAgent.name == name, SyncAgent.revoked_at.is_(None))
    )


async def agents(session: AsyncSession) -> list[SyncAgent]:
    return list(await session.scalars(select(SyncAgent).where(SyncAgent.revoked_at.is_(None))))


async def snapshot(
    session: AsyncSession, snapshot_id: uuid.UUID, *, lock: bool = False
) -> SyncSnapshot | None:
    """Con lock=True blocca la riga fino al commit (conferme concorrenti, snapshot nuovi)."""
    return await session.get(
        SyncSnapshot, snapshot_id, with_for_update=lock, populate_existing=lock
    )


async def supersede_pending(session: AsyncSession, now: datetime) -> None:
    await session.execute(
        update(SyncSnapshot)
        .where(SyncSnapshot.status == "pending_confirmation")
        .values(status="superseded", decided_at=now, decided_by="snapshot successivo")
    )


async def pending(session: AsyncSession) -> SyncSnapshot | None:
    return await session.scalar(
        select(SyncSnapshot)
        .where(SyncSnapshot.status == "pending_confirmation")
        .order_by(SyncSnapshot.received_at.desc())
        .limit(1)
    )


async def recent(session: AsyncSession, limit: int) -> list[tuple[SyncSnapshot, str]]:
    rows = await session.execute(
        select(SyncSnapshot, SyncAgent.name)
        .join(SyncAgent, SyncAgent.id == SyncSnapshot.agent_id)
        .order_by(SyncSnapshot.received_at.desc())
        .limit(limit)
    )
    return [(s, name) for s, name in rows]


async def agent_name(session: AsyncSession, agent_id: uuid.UUID) -> str:
    return (await session.get(SyncAgent, agent_id)).name
