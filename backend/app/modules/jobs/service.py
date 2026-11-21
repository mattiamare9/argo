"""Coda persistente su PostgreSQL (ADR-006).

Ogni funzione che cambia lo stato di un job fa commit: il worker esegue l'handler fuori
da qualsiasi transazione, perché parla con servizi esterni.
"""

import logging
import uuid
from collections.abc import Awaitable, Callable, Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.models import Job, JobStatus, WorkerHeartbeat

HEARTBEAT_INTERVAL = timedelta(seconds=30)
HEARTBEAT_STALE_AFTER = timedelta(minutes=2)

logger = logging.getLogger(__name__)

Handler = Callable[[dict[str, Any]], Awaitable[None]]

BASE_BACKOFF = timedelta(seconds=30)
MAX_BACKOFF = timedelta(hours=1)
LEASE = timedelta(minutes=5)  # oltre questo tempo un job in PROCESSING si considera abbandonato
DEFAULT_MAX_ATTEMPTS = 10  # ~4 ore di tentativi con il backoff sotto


class PermanentError(Exception):
    """Ritentare non servirebbe: il job fallisce subito."""


class ManualActionRequired(Exception):
    """Serve un'azione umana; il messaggio dice quale."""


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def backoff(attempt: int) -> timedelta:
    """30 s, 1 min, 2 min, … fino a 1 ora. Pochi job: nessun jitter necessario."""
    return min(BASE_BACKOFF * 2 ** min(attempt - 1, 20), MAX_BACKOFF)


async def enqueue(
    db: AsyncSession,
    kind: str,
    payload: dict[str, Any],
    *,
    idempotency_key: str,
    group_id: uuid.UUID | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    now: datetime | None = None,
) -> uuid.UUID:
    """Accoda un job nella transazione del chiamante. Stessa chiave → stesso job."""
    statement = (
        insert(Job)
        .values(
            id=uuid.uuid4(),
            kind=kind,
            payload=payload,
            idempotency_key=idempotency_key,
            group_id=group_id,
            status=JobStatus.PENDING,
            attempts=0,
            max_attempts=max_attempts,
            run_after=_now(now),
        )
        .on_conflict_do_nothing(index_elements=["idempotency_key"])
    )
    await db.execute(statement)
    return await db.scalar(select(Job.id).where(Job.idempotency_key == idempotency_key))


async def claim(
    db: AsyncSession, *, now: datetime | None = None, kinds: Iterable[str] | None = None
) -> Job | None:
    now = _now(now)
    query = (
        select(Job)
        .where(
            or_(
                (Job.status.in_([JobStatus.PENDING, JobStatus.RETRYING])) & (Job.run_after <= now),
                (Job.status == JobStatus.PROCESSING) & (Job.locked_until < now),
            )
        )
        .order_by(Job.run_after)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if kinds is not None:
        query = query.where(Job.kind.in_(list(kinds)))
    job = await db.scalar(query)
    if job is None:
        await db.commit()
        return None
    job.status = JobStatus.PROCESSING
    job.attempts += 1
    job.locked_until = now + LEASE
    job.updated_at = now
    await db.commit()
    return job


async def _get(db: AsyncSession, job_id: uuid.UUID) -> Job:
    job = await db.get(Job, job_id)
    if job is None:
        raise LookupError(str(job_id))
    return job


async def complete(db: AsyncSession, job_id: uuid.UUID, *, now: datetime | None = None) -> None:
    job = await _get(db, job_id)
    job.status, job.locked_until, job.last_error = JobStatus.SUCCESS, None, None
    job.finished_at = job.updated_at = _now(now)
    await db.commit()


async def fail(
    db: AsyncSession,
    job_id: uuid.UUID,
    error: str,
    *,
    retryable: bool = True,
    now: datetime | None = None,
) -> None:
    now = _now(now)
    job = await _get(db, job_id)
    job.last_error, job.locked_until, job.updated_at = error[:2000], None, now
    if retryable and job.attempts < job.max_attempts:
        job.status = JobStatus.RETRYING
        job.run_after = now + backoff(job.attempts)
    else:
        job.status, job.finished_at = JobStatus.FAILED, now
    await db.commit()


async def require_manual(
    db: AsyncSession, job_id: uuid.UUID, message: str, *, now: datetime | None = None
) -> None:
    job = await _get(db, job_id)
    job.status, job.last_error, job.locked_until = JobStatus.MANUAL_PENDING, message, None
    job.updated_at = _now(now)
    await db.commit()


async def retry_now(db: AsyncSession, job_id: uuid.UUID, *, now: datetime | None = None) -> Job:
    """Rimette in coda un job fallito, con un nuovo giro completo di tentativi."""
    job = await _get(db, job_id)
    if job.status not in (JobStatus.FAILED, JobStatus.RETRYING):
        raise ValueError("solo i job falliti o in attesa di nuovo tentativo")
    job.status, job.run_after, job.finished_at = JobStatus.RETRYING, _now(now), None
    job.max_attempts = job.attempts + DEFAULT_MAX_ATTEMPTS
    await db.commit()
    return job


async def resolve_manual(
    db: AsyncSession, job_id: uuid.UUID, *, by: str, now: datetime | None = None
) -> Job:
    job = await _get(db, job_id)
    if job.status != JobStatus.MANUAL_PENDING:
        raise ValueError("il job non attende un'azione manuale")
    job.status, job.resolved_by = JobStatus.SUCCESS, by
    job.finished_at = job.updated_at = _now(now)
    await db.commit()
    return job


async def run_once(
    db: AsyncSession, handlers: dict[str, Handler], *, now: datetime | None = None
) -> bool:
    """Esegue al massimo un job. Restituisce False se non c'era nulla da fare."""
    job = await claim(db, now=now)
    if job is None:
        return False
    handler = handlers.get(job.kind)
    try:
        if handler is None:
            raise PermanentError(f"nessun handler per {job.kind}")
        await handler(job.payload)
    except ManualActionRequired as exc:
        await require_manual(db, job.id, str(exc), now=now)
    except PermanentError as exc:
        logger.warning("job %s (%s) fallito definitivamente: %s", job.id, job.kind, exc)
        await fail(db, job.id, str(exc), retryable=False, now=now)
    except Exception as exc:  # qualunque errore esterno: si ritenta
        logger.warning("job %s (%s) fallito, nuovo tentativo: %s", job.id, job.kind, exc)
        await fail(db, job.id, f"{type(exc).__name__}: {exc}", now=now)
    else:
        await complete(db, job.id, now=now)
    return True


async def by_group(db: AsyncSession, group_ids: Iterable[uuid.UUID]) -> list[Job]:
    rows = await db.scalars(
        select(Job).where(Job.group_id.in_(list(group_ids))).order_by(Job.created_at, Job.kind)
    )
    return list(rows)


async def beat(db: AsyncSession, worker_id: str, *, now: datetime | None = None) -> None:
    now = _now(now)
    statement = insert(WorkerHeartbeat).values(worker_id=worker_id, last_seen_at=now)
    await db.execute(
        statement.on_conflict_do_update(
            index_elements=["worker_id"], set_={"last_seen_at": statement.excluded.last_seen_at}
        )
    )
    await db.commit()


async def worker_status(db: AsyncSession, *, now: datetime | None = None) -> str:
    """\"ok\" se un worker è vivo da meno di 2 minuti, \"stale\" se no, \"unknown\" se mai visto."""
    latest = await db.scalar(select(func.max(WorkerHeartbeat.last_seen_at)))
    if latest is None:
        return "unknown"
    return "ok" if _now(now) - latest < HEARTBEAT_STALE_AFTER else "stale"
