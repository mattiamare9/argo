from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules import jobs


async def test_beat_upserts_and_status_goes_stale(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    assert await jobs.worker_status(session, now=now) == "unknown"
    await jobs.beat(session, "w1", now=now)
    await jobs.beat(session, "w1", now=now)  # stesso worker: aggiorna, non duplica
    assert await jobs.worker_status(session, now=now) == "ok"
    assert await jobs.worker_status(session, now=now + timedelta(minutes=3)) == "stale"
