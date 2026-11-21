import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.modules import jobs
from app.modules.jobs import JobStatus, ManualActionRequired, PermanentError
from app.modules.jobs.models import Job

NOW = datetime(2026, 11, 21, 10, 0, tzinfo=UTC)


async def test_enqueue_is_idempotent(session) -> None:
    first = await jobs.enqueue(session, "demo", {"a": 1}, idempotency_key="k1")
    second = await jobs.enqueue(session, "demo", {"a": 2}, idempotency_key="k1")
    assert first == second


async def test_claim_marks_processing_and_counts_attempt(session) -> None:
    await jobs.enqueue(session, "demo", {}, idempotency_key="k2", now=NOW)
    job = await jobs.claim(session, now=NOW)
    assert job.status == JobStatus.PROCESSING
    assert job.attempts == 1
    assert await jobs.claim(session, now=NOW) is None  # già preso


async def test_failure_schedules_retry_with_backoff(session) -> None:
    await jobs.enqueue(session, "demo", {}, idempotency_key="k3", now=NOW)
    job = await jobs.claim(session, now=NOW)
    await jobs.fail(session, job.id, "timeout", now=NOW)
    assert job.status == JobStatus.RETRYING
    assert job.run_after == NOW + jobs.backoff(1)
    assert await jobs.claim(session, now=NOW) is None  # non ancora
    assert await jobs.claim(session, now=job.run_after) is not None


def test_backoff_grows_and_is_capped() -> None:
    assert jobs.backoff(1) < jobs.backoff(2) < jobs.backoff(3)
    assert jobs.backoff(50) == jobs.MAX_BACKOFF


async def test_job_fails_after_max_attempts(session) -> None:
    await jobs.enqueue(session, "demo", {}, idempotency_key="k4", now=NOW, max_attempts=2)
    for attempt in range(2):
        job = await jobs.claim(session, now=NOW + timedelta(days=attempt))
        await jobs.fail(session, job.id, "giù", now=NOW + timedelta(days=attempt))
    assert job.status == JobStatus.FAILED
    assert job.last_error == "giù"


async def test_permanent_error_fails_immediately(session) -> None:
    await jobs.enqueue(session, "demo", {}, idempotency_key="k5", now=NOW)
    job = await jobs.claim(session, now=NOW)
    await jobs.fail(session, job.id, "utente inesistente", now=NOW, retryable=False)
    assert job.status == JobStatus.FAILED


async def test_expired_lease_is_reclaimed(session) -> None:
    await jobs.enqueue(session, "demo", {}, idempotency_key="k6", now=NOW)
    job = await jobs.claim(session, now=NOW)
    later = NOW + jobs.LEASE + timedelta(seconds=1)
    again = await jobs.claim(session, now=later)
    assert again.id == job.id
    assert again.attempts == 2


async def test_run_once_dispatches_to_handler(session) -> None:
    seen = []

    async def ok(payload: dict) -> None:
        seen.append(payload)

    async def manual(payload: dict) -> None:
        raise ManualActionRequired("disattivare a mano su FatturaFacile")

    async def broken(payload: dict) -> None:
        raise PermanentError("configurazione mancante")

    handlers = {"ok": ok, "manual": manual, "broken": broken}
    ids = [
        await jobs.enqueue(session, kind, {"k": kind}, idempotency_key=kind, now=NOW)
        for kind in handlers
    ]
    while await jobs.run_once(session, handlers, now=NOW):
        pass
    statuses = [(await session.get(Job, i)).status for i in ids]
    assert statuses == [JobStatus.SUCCESS, JobStatus.MANUAL_PENDING, JobStatus.FAILED]
    assert seen == [{"k": "ok"}]


async def test_unknown_kind_fails_permanently(session) -> None:
    job_id = await jobs.enqueue(session, "sconosciuto", {}, idempotency_key="k7", now=NOW)
    await jobs.run_once(session, {}, now=NOW)
    assert (await session.get(Job, job_id)).status == JobStatus.FAILED


async def test_retry_and_resolve(session) -> None:
    job_id = await jobs.enqueue(session, "demo", {}, idempotency_key="k8", now=NOW)
    job = await jobs.claim(session, now=NOW)
    await jobs.fail(session, job.id, "x", now=NOW, retryable=False)
    await jobs.retry_now(session, job_id, now=NOW)
    assert job.status == JobStatus.RETRYING and job.run_after == NOW
    job.status = JobStatus.MANUAL_PENDING
    await jobs.resolve_manual(session, job_id, by="admin", now=NOW)
    assert job.status == JobStatus.SUCCESS


@pytest.mark.parametrize("workers", [4])
async def test_concurrent_workers_never_take_the_same_job(engine: AsyncEngine, workers) -> None:
    """Connessioni reali e parallele: SKIP LOCKED deve distribuire i job senza duplicati."""
    tag = uuid.uuid4().hex[:8]
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        for i in range(20):
            await jobs.enqueue(db, f"conc-{tag}", {"i": i}, idempotency_key=f"{tag}-{i}")
        await db.commit()

    taken: list[uuid.UUID] = []

    async def worker() -> None:
        async with maker() as db:
            while job := await jobs.claim(db, kinds={f"conc-{tag}"}):
                taken.append(job.id)
                await asyncio.sleep(0)

    try:
        await asyncio.gather(*(worker() for _ in range(workers)))
        assert len(taken) == 20
        assert len(set(taken)) == 20
    finally:
        async with maker() as db:
            await db.execute(delete(Job).where(Job.kind == f"conc-{tag}"))
            await db.commit()
