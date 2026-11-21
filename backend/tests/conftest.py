from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

BACKEND_DIR = Path(__file__).resolve().parent.parent


class TestSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ARGO_TEST_", env_file=".env", extra="ignore")

    database_url: str


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return TestSettings().database_url


@pytest.fixture(scope="session")
def migrated_database(test_database_url: str) -> str:
    """Schema ricreato da zero a ogni sessione: verifica anche downgrade e upgrade."""
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", test_database_url)
    cfg.attributes["configure_logger"] = False
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    return test_database_url


@pytest.fixture(scope="session")
async def engine(migrated_database: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_database)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Sessione dentro una transazione annullata a fine test: il DB di test resta pulito."""
    async with engine.connect() as conn:
        transaction = await conn.begin()
        async with AsyncSession(bind=conn, join_transaction_mode="create_savepoint") as session:
            yield session
        await transaction.rollback()
