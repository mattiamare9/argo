import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules import audit, jobs
from app.modules.provisioning.service import RunOut, list_runs
from app.modules.sessions import CurrentUser, require_csrf, require_role

router = APIRouter(prefix="/api/provisioning", tags=["provisioning"])
DASHBOARD = require_role("iam-admin", "iam-owner")
ADMIN = require_role("iam-admin")


@router.get("/runs", dependencies=[Depends(DASHBOARD)])
async def get_runs(only_open: bool = False, db: AsyncSession = Depends(get_db)) -> list[RunOut]:
    return await list_runs(db, only_open=only_open)


@router.post("/jobs/{job_id}/retry", dependencies=[Depends(require_csrf)])
async def retry_job(
    job_id: uuid.UUID,
    user: CurrentUser = Depends(ADMIN),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    try:
        await jobs.retry_now(db, job_id)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    await audit.record(
        db,
        actor=f"user:{user.username}",
        action="job.retry",
        outcome="success",
        target_type="job",
        target_id=str(job_id),
    )
    await db.commit()
    return {"status": "RETRYING"}


@router.post("/jobs/{job_id}/resolve", dependencies=[Depends(require_csrf)])
async def resolve_job(
    job_id: uuid.UUID,
    user: CurrentUser = Depends(DASHBOARD),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Conferma che un'azione manuale richiesta è stata fatta."""
    try:
        await jobs.resolve_manual(db, job_id, by=user.username)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    await audit.record(
        db,
        actor=f"user:{user.username}",
        action="job.manual_resolved",
        outcome="success",
        target_type="job",
        target_id=str(job_id),
    )
    await db.commit()
    return {"status": "SUCCESS"}
