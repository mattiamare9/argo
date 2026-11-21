from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_engine(database_url: str) -> AsyncEngine:
    # Pool piccolo: 10–30 utenti, risorse limitate.
    return create_async_engine(database_url, pool_size=5, max_overflow=5, pool_pre_ping=True)
