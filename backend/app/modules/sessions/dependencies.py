from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.sessions import service
from app.modules.sessions.service import CurrentUser

SESSION_COOKIE = "argo_session"
CSRF_HEADER = "X-Argo-CSRF"


async def current_user(request: Request, db: AsyncSession = Depends(get_db)) -> CurrentUser:
    user = await service.get_current(db, request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Accesso richiesto")
    return user


def require_role(*roles: str) -> Callable[..., Awaitable[CurrentUser]]:
    """Dipendenza: l'utente deve avere almeno uno dei ruoli indicati."""

    async def dependency(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if not user.roles.intersection(roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Non hai accesso a questa funzione")
        return user

    return dependency


async def require_csrf(request: Request) -> None:
    # Nessun CORS abilitato: un sito esterno non può inviare header personalizzati.
    if request.headers.get(CSRF_HEADER) != "1":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Richiesta non valida")
