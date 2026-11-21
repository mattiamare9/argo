from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine


def create_engine(database_url: str) -> AsyncEngine:
    # Pool piccolo: 10–30 utenti, risorse limitate.
    return create_async_engine(database_url, pool_size=5, max_overflow=5, pool_pre_ping=True)


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """Dipendenza FastAPI: una sessione DB per richiesta. Il commit lo decide il service."""
    async with request.app.state.sessionmaker() as session:
        yield session
