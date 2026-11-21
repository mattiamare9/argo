from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.employees import service
from app.modules.employees.schemas import EmployeePage
from app.modules.sessions import require_role

router = APIRouter(
    prefix="/api/employees",
    tags=["employees"],
    dependencies=[Depends(require_role("iam-admin", "iam-owner"))],
)


@router.get("")
async def list_employees(
    search: str | None = Query(None, max_length=100),
    status: Literal["ACTIVE", "INACTIVE"] | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=service.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
) -> EmployeePage:
    return await service.list_employees(
        db, search=search, status=status, page=page, page_size=page_size
    )
