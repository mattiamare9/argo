import hashlib
import secrets
import uuid
from collections import Counter
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules import audit, employees, provisioning
from app.modules.employees import ChangeKind, EmployeeRecord, PlannedChange
from app.modules.synchronization import repository
from app.modules.synchronization.models import SyncAgent, SyncSnapshot
from app.modules.synchronization.schemas import (
    AgentOut,
    PendingDeactivation,
    PendingSnapshotOut,
    SnapshotIn,
    SnapshotOut,
    SnapshotResult,
    SyncOverview,
)


class SnapshotRejected(Exception):
    """Snapshot non applicabile: il motivo è per l'agent e per la dashboard."""


class SnapshotNotPending(Exception):
    pass


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def create_agent(db: AsyncSession, name: str) -> str:
    """Crea un agent e restituisce la chiave API in chiaro (mostrata una sola volta)."""
    key = f"argo_{secrets.token_urlsafe(32)}"
    await repository.add(db, SyncAgent(name=name, key_hash=hash_key(key)))
    await audit.record(
        db, actor="cli", action="sync.agent_created", outcome="success", target_id=name
    )
    await db.commit()
    return key


async def authenticate(db: AsyncSession, key: str | None) -> SyncAgent | None:
    if not key:
        return None
    agent = await repository.agent_by_key_hash(db, hash_key(key))
    if agent is not None:
        agent.last_seen_at = datetime.now(UTC)
    return agent


async def set_agent_status(db: AsyncSession, agent: SyncAgent, ok: bool, message: str) -> None:
    if ok:
        agent.last_error = agent.last_error_at = None
    else:
        agent.last_error, agent.last_error_at = message, datetime.now(UTC)
        await audit.record(
            db,
            actor=f"agent:{agent.name}",
            action="sync.source_error",
            outcome="failure",
            details={"message": message},
        )
    await db.commit()


def _summary(plan: list[PlannedChange], missing: int) -> dict[str, int]:
    counts = Counter(change.kind.value for change in plan)
    summary = {kind.value: counts.get(kind.value, 0) for kind in ChangeKind}
    summary["missing_from_source"] = missing
    return summary


def _duplicates(values: list[str]) -> list[str]:
    return sorted(v for v, n in Counter(values).items() if n > 1)


async def receive_snapshot(
    db: AsyncSession, agent: SyncAgent, payload: SnapshotIn, *, threshold: int
) -> SnapshotResult:
    existing = await repository.snapshot(db, payload.snapshot_id)
    if existing is not None:
        await db.commit()  # salva last_seen_at
        if existing.status == "rejected":
            raise SnapshotRejected(existing.detail)
        return SnapshotResult(snapshot_id=existing.id, status="duplicate", summary=existing.summary)

    agent.last_error = agent.last_error_at = None
    records = [r.to_record() for r in payload.records]
    snapshot = SyncSnapshot(
        id=payload.snapshot_id,
        agent_id=agent.id,
        source=payload.source,
        read_at=payload.read_at,
        records=[r.model_dump() for r in records],
        status="rejected",
    )
    actor = f"agent:{agent.name}"

    problem = await _validate(db, records)
    if problem:
        snapshot.detail = problem
        await repository.add(db, snapshot)
        await audit.record(
            db,
            actor=actor,
            action="sync.snapshot_rejected",
            outcome="failure",
            target_type="snapshot",
            target_id=str(snapshot.id),
            details={"detail": problem},
        )
        await db.commit()
        raise SnapshotRejected(problem)

    plan = await employees.plan_changes(db, records)
    snapshot.summary = _summary(plan, await employees.count_missing(db, records))
    await repository.supersede_pending(db, datetime.now(UTC))

    if snapshot.summary[ChangeKind.DEACTIVATED.value] >= threshold:
        snapshot.status = "pending_confirmation"
        await repository.add(db, snapshot)
        await audit.record(
            db,
            actor=actor,
            action="sync.snapshot_pending",
            outcome="success",
            target_type="snapshot",
            target_id=str(snapshot.id),
            details=snapshot.summary,
        )
        await db.commit()
        return SnapshotResult(
            snapshot_id=snapshot.id, status="pending_confirmation", summary=snapshot.summary
        )

    snapshot.status = "applied"
    await repository.add(db, snapshot)
    applied = await employees.apply_changes(db, plan, source=payload.source, actor=actor)
    await provisioning.on_changes(db, applied, triggered_by=actor)
    await audit.record(
        db,
        actor=actor,
        action="sync.snapshot_applied",
        outcome="success",
        target_type="snapshot",
        target_id=str(snapshot.id),
        details=snapshot.summary,
    )
    await db.commit()
    return SnapshotResult(snapshot_id=snapshot.id, status="applied", summary=snapshot.summary)


async def _validate(db: AsyncSession, records: list[EmployeeRecord]) -> str | None:
    dup_ids = _duplicates([employees.key_of(r.employee_id) for r in records])
    if dup_ids:
        return f"employee_id duplicati: {', '.join(dup_ids)}"
    dup_emails = _duplicates([r.email.lower() for r in records])
    if dup_emails:
        return f"email duplicate: {', '.join(dup_emails)}"
    conflicts = await employees.find_email_conflicts(db, records)
    if conflicts:
        return f"email già assegnate ad altri dipendenti: {', '.join(conflicts)}"
    return None


async def confirm(db: AsyncSession, snapshot_id: uuid.UUID, user: str) -> SnapshotOut:
    snapshot = await _pending(db, snapshot_id)
    records = [EmployeeRecord(**r) for r in snapshot.records]
    # Ripianifica sullo stato attuale: l'anagrafica può essere cambiata dalla ricezione.
    problem = await _validate(db, records)
    if problem:
        snapshot.status, snapshot.detail = "rejected", problem
    else:
        plan = await employees.plan_changes(db, records)
        snapshot.summary = _summary(plan, await employees.count_missing(db, records))
        applied = await employees.apply_changes(
            db, plan, source=snapshot.source, actor=f"user:{user}"
        )
        await provisioning.on_changes(db, applied, triggered_by=f"user:{user}")
        snapshot.status = "applied"
    snapshot.decided_by, snapshot.decided_at = user, datetime.now(UTC)
    await audit.record(
        db,
        actor=f"user:{user}",
        action="sync.snapshot_confirmed",
        outcome="success" if not problem else "failure",
        target_type="snapshot",
        target_id=str(snapshot.id),
        details=snapshot.summary if not problem else {"detail": problem},
    )
    await db.commit()
    return await _out(db, snapshot)


async def cancel(db: AsyncSession, snapshot_id: uuid.UUID, user: str) -> SnapshotOut:
    snapshot = await _pending(db, snapshot_id)
    snapshot.status, snapshot.decided_by = "cancelled", user
    snapshot.decided_at = datetime.now(UTC)
    await audit.record(
        db,
        actor=f"user:{user}",
        action="sync.snapshot_cancelled",
        outcome="success",
        target_type="snapshot",
        target_id=str(snapshot.id),
    )
    await db.commit()
    return await _out(db, snapshot)


async def overview(db: AsyncSession, recent_limit: int = 10) -> SyncOverview:
    pending = await repository.pending(db)
    pending_out = None
    if pending is not None:
        records = [EmployeeRecord(**r) for r in pending.records]
        plan = await employees.plan_changes(db, records)
        pending_out = PendingSnapshotOut(
            **(await _out(db, pending)).model_dump(),
            deactivations=[
                PendingDeactivation(
                    employee_id=c.record.employee_id,
                    first_name=c.record.first_name,
                    last_name=c.record.last_name,
                )
                for c in plan
                if c.kind is ChangeKind.DEACTIVATED
            ],
        )
    return SyncOverview(
        agents=[
            AgentOut(
                name=a.name,
                last_seen_at=a.last_seen_at,
                last_error=a.last_error,
                last_error_at=a.last_error_at,
            )
            for a in await repository.agents(db)
        ],
        pending=pending_out,
        recent=[_to_out(s, name) for s, name in await repository.recent(db, recent_limit)],
    )


async def _pending(db: AsyncSession, snapshot_id: uuid.UUID) -> SyncSnapshot:
    snapshot = await repository.snapshot(db, snapshot_id, lock=True)
    if snapshot is None or snapshot.status != "pending_confirmation":
        raise SnapshotNotPending(str(snapshot_id))
    return snapshot


async def _out(db: AsyncSession, snapshot: SyncSnapshot) -> SnapshotOut:
    return _to_out(snapshot, await repository.agent_name(db, snapshot.agent_id))


def _to_out(snapshot: SyncSnapshot, agent_name: str) -> SnapshotOut:
    return SnapshotOut(
        snapshot_id=snapshot.id,
        agent=agent_name,
        received_at=snapshot.received_at,
        status=snapshot.status,
        summary=snapshot.summary,
        detail=snapshot.detail,
        decided_by=snapshot.decided_by,
    )
