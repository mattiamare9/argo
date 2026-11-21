import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.applications.models import Application


async def get(db: AsyncSession, application_id: uuid.UUID) -> Application | None:
    return await db.get(Application, application_id)


async def get_by_slug(db: AsyncSession, slug: str) -> Application | None:
    return await db.scalar(select(Application).where(Application.slug == slug))


async def list_all(db: AsyncSession, *, only_enabled: bool = False) -> list[Application]:
    query = select(Application).order_by(Application.name)
    if only_enabled:
        query = query.where(Application.enabled.is_(True))
    return list(await db.scalars(query))
