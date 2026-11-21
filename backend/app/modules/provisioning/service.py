import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules import employees, jobs
from app.modules.employees import AppliedChange, ChangeKind
from app.modules.jobs import Job, JobStatus
from app.modules.provisioning.models import LifecycleRun

RunKind = Literal["onboarding", "offboarding", "reactivation", "profile_update"]
RunStatus = Literal["in_progress", "completed", "partial"]

# Passi per tipo di operazione. Ogni passo è un job indipendente: un errore su uno non
# annulla gli altri (specifica §9.1). Le app custom, la VPN e i SaaS si aggiungono qui.
STEPS: dict[RunKind, list[str]] = {
    "onboarding": ["identity.provision"],
    "reactivation": ["identity.provision"],
    "profile_update": ["identity.update_profile"],
    "offboarding": ["identity.disable", "identity.logout", "dashboard.revoke_sessions"],
}

STEP_LABELS = {
    "identity.provision": "Account e invito passkey",
    "identity.update_profile": "Aggiornamento anagrafica",
    "identity.disable": "Disattivazione account",
    "identity.logout": "Chiusura sessioni di accesso",
    "dashboard.revoke_sessions": "Chiusura sessioni dashboard Argo",
}


def run_kind(change: AppliedChange) -> RunKind | None:
    if change.kind is ChangeKind.DEACTIVATED:
        return "offboarding"
    if change.kind is ChangeKind.REACTIVATED:
        return "reactivation"
    if change.kind is ChangeKind.CREATED:
        return "onboarding" if change.status == "ACTIVE" else None
    if change.kind is ChangeKind.UPDATED and change.status == "ACTIVE":
        return "profile_update"  # chi è inattivo non ha accessi da aggiornare
    return None


async def on_changes(
    db: AsyncSession, changes: list[AppliedChange], *, triggered_by: str
) -> list[uuid.UUID]:
    """Crea i run e i loro job nella transazione del chiamante (nessun evento perso)."""
    run_ids = []
    for change in changes:
        kind = run_kind(change)
        if kind is None:
            continue
        run = LifecycleRun(
            employee_id=change.employee_id,
            employee_name=f"{change.first_name} {change.last_name}",
            kind=kind,
            triggered_by=triggered_by,
        )
        db.add(run)
        await db.flush()
        payload = {
            "employee_id": change.employee_id,
            "email": change.email,
            "first_name": change.first_name,
            "last_name": change.last_name,
        }
        for step in STEPS[kind]:
            await jobs.enqueue(
                db, step, payload, idempotency_key=f"{run.id}:{step}", group_id=run.id
            )
        run_ids.append(run.id)
    return run_ids


class StepOut(BaseModel):
    job_id: uuid.UUID
    kind: str
    label: str
    status: str
    attempts: int
    last_error: str | None
    run_after: datetime
    resolved_by: str | None


class RunOut(BaseModel):
    id: uuid.UUID
    employee_id: str
    employee_name: str
    kind: RunKind
    status: RunStatus
    triggered_by: str
    created_at: datetime
    steps: list[StepOut]


def run_status(steps: list[Job]) -> RunStatus:
    statuses = {s.status for s in steps}
    if statuses <= {JobStatus.SUCCESS}:
        return "completed"
    if statuses & {JobStatus.FAILED, JobStatus.MANUAL_PENDING}:
        return "partial"  # resta visibile finché non viene risolto
    return "in_progress"


async def list_runs(db: AsyncSession, *, only_open: bool, limit: int = 50) -> list[RunOut]:
    runs = list(
        await db.scalars(select(LifecycleRun).order_by(LifecycleRun.created_at.desc()).limit(limit))
    )
    steps_by_run: dict[uuid.UUID, list[Job]] = {r.id: [] for r in runs}
    for job in await jobs.by_group(db, steps_by_run):
        steps_by_run[job.group_id].append(job)
    result = []
    for run in runs:
        steps = steps_by_run[run.id]
        status = run_status(steps)
        if only_open and status == "completed":
            continue
        result.append(
            RunOut(
                id=run.id,
                employee_id=run.employee_id,
                employee_name=run.employee_name,
                kind=run.kind,
                status=status,
                triggered_by=run.triggered_by,
                created_at=run.created_at,
                steps=[
                    StepOut(
                        job_id=s.id,
                        kind=s.kind,
                        label=STEP_LABELS.get(s.kind, s.kind),
                        status=s.status,
                        attempts=s.attempts,
                        last_error=s.last_error,
                        run_after=s.run_after,
                        resolved_by=s.resolved_by,
                    )
                    for s in steps
                ],
            )
        )
    return result


KeyState = Literal["hung", "returned", "pending"]


class KeyOut(BaseModel):
    name: str
    state: KeyState


class PlateOut(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    status: Literal["ACTIVE", "INACTIVE"]
    keys: list[KeyOut]


def key_state(status: str, last_run: RunStatus | None) -> KeyState:
    """Chiave appesa = accesso attivo; gancio vuoto = riconsegnato; ambra = non completato."""
    if last_run in ("in_progress", "partial"):
        return "pending"
    if status == "INACTIVE":
        return "returned"
    # Attivo senza alcun run: l'account non è mai stato creato da Argo, va verificato.
    return "hung" if last_run == "completed" else "pending"


async def board(db: AsyncSession) -> list[PlateOut]:
    """Il quadro accessi: una targhetta per dipendente, una chiave per accesso gestito.

    Oggi l'unico accesso gestito è l'account aziendale (identity provider); app custom,
    VPN e SaaS aggiungeranno chiavi (Fase 5).
    """
    # shortcut: una sola pagina (100 persone); paginare il quadro se l'azienda cresce oltre.
    people = await employees.list_employees(db, page_size=employees.MAX_PAGE_SIZE)
    latest: dict[str, RunStatus] = {}
    for run in await list_runs(db, only_open=False, limit=1000):
        latest.setdefault(run.employee_id, run.status)  # list_runs è dal più recente
    return [
        PlateOut(
            employee_id=p.employee_id,
            first_name=p.first_name,
            last_name=p.last_name,
            status=p.status,
            keys=[
                KeyOut(
                    name="Account aziendale", state=key_state(p.status, latest.get(p.employee_id))
                )
            ],
        )
        for p in people.items
    ]
