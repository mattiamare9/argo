from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.audit import service
from app.modules.audit.schemas import AuditPage
from app.modules.sessions import require_role

router = APIRouter(
    prefix="/api/audit",
    tags=["audit"],
    dependencies=[Depends(require_role("iam-admin", "iam-owner"))],
)


@router.get("")
async def list_events(
    search: str | None = Query(None, max_length=100),
    outcome: Literal["success", "failure"] | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=service.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
) -> AuditPage:
    return await service.list_events(
        db, search=search, outcome=outcome, page=page, page_size=page_size
    )
