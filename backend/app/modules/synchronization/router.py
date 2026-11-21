import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, StringConstraints
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.sessions import CurrentUser, require_csrf, require_role
from app.modules.synchronization import service
from app.modules.synchronization.models import SyncAgent
from app.modules.synchronization.schemas import (
    AgentStatusIn,
    SnapshotIn,
    SnapshotOut,
    SnapshotResult,
    SyncOverview,
)

agent_router = APIRouter(prefix="/api/v1/sync", tags=["sync-agent"])
dashboard_router = APIRouter(prefix="/api/sync", tags=["sync"])

DASHBOARD = require_role("iam-admin", "iam-owner")
ADMIN = require_role("iam-admin")


class NewAgentIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[a-z0-9-]{1,60}$")]


class NewAgentOut(BaseModel):
    name: str
    key: str  # mostrata una sola volta


@dashboard_router.post("/agents", status_code=201, dependencies=[Depends(require_csrf)])
async def create_agent(
    payload: NewAgentIn,
    user: CurrentUser = Depends(ADMIN),
    db: AsyncSession = Depends(get_db),
) -> NewAgentOut:
    try:
        key = await service.create_agent(db, payload.name, actor=f"user:{user.username}")
    except service.AgentConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return NewAgentOut(name=payload.name, key=key)


@dashboard_router.post(
    "/agents/{name}/revoke", status_code=204, dependencies=[Depends(require_csrf)]
)
async def revoke_agent(
    name: str,
    user: CurrentUser = Depends(ADMIN),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await service.revoke_agent(db, name, actor=f"user:{user.username}")
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Programma non trovato") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def current_agent(request: Request, db: AsyncSession = Depends(get_db)) -> SyncAgent:
    scheme, _, key = request.headers.get("Authorization", "").partition(" ")
    agent = await service.authenticate(db, key if scheme.lower() == "bearer" else None)
    if agent is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chiave agent non valida")
    return agent


@agent_router.post("/snapshots")
async def post_snapshot(
    payload: SnapshotIn,
    request: Request,
    agent: SyncAgent = Depends(current_agent),
    db: AsyncSession = Depends(get_db),
) -> SnapshotResult:
    threshold = request.app.state.settings.mass_deactivation_threshold
    try:
        return await service.receive_snapshot(db, agent, payload, threshold=threshold)
    except service.SnapshotRejected as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


@agent_router.post("/agent-status", status_code=status.HTTP_204_NO_CONTENT)
async def post_agent_status(
    payload: AgentStatusIn,
    agent: SyncAgent = Depends(current_agent),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await service.set_agent_status(db, agent, payload.ok, payload.message)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@dashboard_router.get("/overview", dependencies=[Depends(DASHBOARD)])
async def get_overview(db: AsyncSession = Depends(get_db)) -> SyncOverview:
    return await service.overview(db)


@dashboard_router.post("/snapshots/{snapshot_id}/confirm", dependencies=[Depends(require_csrf)])
async def confirm_snapshot(
    snapshot_id: uuid.UUID,
    user: CurrentUser = Depends(DASHBOARD),
    db: AsyncSession = Depends(get_db),
) -> SnapshotOut:
    try:
        return await service.confirm(db, snapshot_id, user.username)
    except service.SnapshotNotPending as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Nessuna conferma in attesa") from exc


@dashboard_router.post("/snapshots/{snapshot_id}/cancel", dependencies=[Depends(require_csrf)])
async def cancel_snapshot(
    snapshot_id: uuid.UUID,
    user: CurrentUser = Depends(DASHBOARD),
    db: AsyncSession = Depends(get_db),
) -> SnapshotOut:
    try:
        return await service.cancel(db, snapshot_id, user.username)
    except service.SnapshotNotPending as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Nessuna conferma in attesa") from exc
