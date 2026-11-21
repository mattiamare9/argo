from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.sessions import service
from app.modules.sessions.dependencies import SESSION_COOKIE, current_user, require_csrf
from app.modules.sessions.oidc import OidcClient, OidcError
from app.modules.sessions.service import CurrentUser, LoginRejected

LOGIN_COOKIE = "argo_login"

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Me(BaseModel):
    username: str
    display_name: str
    email: str | None
    roles: list[str]


class LogoutResult(BaseModel):
    logout_url: str


def get_oidc(request: Request) -> OidcClient:
    oidc: OidcClient | None = request.app.state.oidc
    if oidc is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Accesso non configurato")
    return oidc


def _secure_cookies(request: Request) -> bool:
    return request.app.state.settings.environment == "production"


@router.get("/login")
async def login(
    request: Request,
    next: str | None = None,
    db: AsyncSession = Depends(get_db),
    oidc: OidcClient = Depends(get_oidc),
) -> RedirectResponse:
    try:
        url, state = await service.start_login(db, oidc, next)
    except OidcError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Servizio di accesso non raggiungibile"
        ) from exc
    response = RedirectResponse(url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        LOGIN_COOKIE,
        state,
        max_age=int(service.LOGIN_ATTEMPT_TTL.total_seconds()),
        path="/api/auth",
        httponly=True,
        samesite="lax",
        secure=_secure_cookies(request),
    )
    return response


@router.get("/callback")
async def callback(
    request: Request,
    state: str,
    code: str,
    db: AsyncSession = Depends(get_db),
    oidc: OidcClient = Depends(get_oidc),
) -> RedirectResponse:
    try:
        token, next_path = await service.complete_login(
            db, oidc, state=state, code=code, browser_state=request.cookies.get(LOGIN_COOKIE)
        )
    except LoginRejected as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Accesso non riuscito: {exc}") from exc
    except OidcError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Servizio di accesso non raggiungibile"
        ) from exc
    response = RedirectResponse(next_path, status_code=status.HTTP_302_FOUND)
    response.delete_cookie(LOGIN_COOKIE, path="/api/auth")
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(service.ABSOLUTE_TIMEOUT.total_seconds()),
        path="/",
        httponly=True,
        samesite="lax",
        secure=_secure_cookies(request),
    )
    return response


@router.get("/me")
async def me(user: CurrentUser = Depends(current_user)) -> Me:
    return Me(
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        roles=sorted(user.roles),
    )


@router.post("/logout", dependencies=[Depends(require_csrf)])
async def logout(
    request: Request,
    user: CurrentUser = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    oidc: OidcClient = Depends(get_oidc),
) -> LogoutResult:
    await service.logout(db, request.cookies[SESSION_COOKIE], user)
    settings = request.app.state.settings
    try:
        logout_url = await oidc.end_session_url(f"{settings.public_url}/")
    except OidcError:
        logout_url = "/"  # la sessione Argo è chiusa comunque
    return LogoutResult(logout_url=logout_url)
