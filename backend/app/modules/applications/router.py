import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.applications import service
from app.modules.applications.schemas import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationUpdate,
)
from app.modules.sessions import CurrentUser, require_csrf, require_role

router = APIRouter(prefix="/api/applications", tags=["applications"])
DASHBOARD = require_role("iam-admin", "iam-owner")
ADMIN = require_role("iam-admin")

_ERRORS = {
    service.ApplicationNotFound: (status.HTTP_404_NOT_FOUND, "Applicazione non trovata"),
    service.ApplicationConflict: (status.HTTP_409_CONFLICT, None),
    service.InvalidApplication: (status.HTTP_422_UNPROCESSABLE_CONTENT, None),
}


def _http_error(exc: Exception) -> HTTPException:
    code, message = _ERRORS[type(exc)]
    return HTTPException(code, message or str(exc))


@router.get("", dependencies=[Depends(DASHBOARD)])
async def list_applications(db: AsyncSession = Depends(get_db)) -> list[ApplicationOut]:
    return await service.list_applications(db)


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_csrf)])
async def create_application(
    data: ApplicationCreate,
    request: Request,
    user: CurrentUser = Depends(ADMIN),
    db: AsyncSession = Depends(get_db),
) -> ApplicationOut:
    try:
        return await service.create(db, request.app.state.settings, data, actor=user.username)
    except (service.ApplicationConflict, service.InvalidApplication) as exc:
        raise _http_error(exc) from exc


@router.patch("/{application_id}", dependencies=[Depends(require_csrf)])
async def update_application(
    application_id: uuid.UUID,
    data: ApplicationUpdate,
    request: Request,
    user: CurrentUser = Depends(ADMIN),
    db: AsyncSession = Depends(get_db),
) -> ApplicationOut:
    try:
        return await service.update(
            db, request.app.state.settings, application_id, data, actor=user.username
        )
    except (
        service.ApplicationNotFound,
        service.ApplicationConflict,
        service.InvalidApplication,
    ) as exc:
        raise _http_error(exc) from exc


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_application(
    application_id: uuid.UUID,
    user: CurrentUser = Depends(ADMIN),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await service.delete(db, application_id, actor=user.username)
    except service.ApplicationNotFound as exc:
        raise _http_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
