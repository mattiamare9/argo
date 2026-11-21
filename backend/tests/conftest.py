from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

BACKEND_DIR = Path(__file__).resolve().parent.parent


class TestSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ARGO_TEST_", env_file=".env", extra="ignore")

    database_url: str
    keycloak_url: str | None = None  # se assente, i test marcati `keycloak` vengono saltati


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return TestSettings().database_url


@pytest.fixture(scope="session")
def keycloak_url() -> str:
    url = TestSettings().keycloak_url
    if not url:
        pytest.skip("ARGO_TEST_KEYCLOAK_URL non impostato: profilo idp non attivo")
    return url


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
async def api(session: AsyncSession, migrated_database: str):
    """App con DB transazionale di test, senza identity provider."""
    from app.core.config import Settings
    from app.db.session import get_db
    from app.main import create_app

    # Nessun segreto da .env: i test non devono dipendere dalla configurazione locale.
    app = create_app(
        Settings(
            database_url=migrated_database,
            mass_deactivation_threshold=3,
            secrets_key=None,
            oidc_client_secret=None,
            keycloak_backend_client_secret=None,
        )
    )
    app.dependency_overrides[get_db] = lambda: session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    await app.state.engine.dispose()


@pytest.fixture
def login_as(session: AsyncSession):
    """Crea una sessione dashboard valida e la imposta come cookie sul client."""
    from datetime import UTC, datetime, timedelta

    from app.modules.sessions.models import UserSession
    from app.modules.sessions.service import hash_token

    async def _login(client: httpx.AsyncClient, *roles: str, username: str = "tester") -> None:
        token = f"token-{username}"
        now = datetime.now(UTC)
        session.add(
            UserSession(
                token_hash=hash_token(token),
                subject=f"sub-{username}",
                username=username,
                display_name=username,
                email=None,
                roles=list(roles),
                last_seen_at=now,
                expires_at=now + timedelta(hours=1),
            )
        )
        await session.flush()
        client.cookies.set("argo_session", token)

    return _login


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Sessione dentro una transazione annullata a fine test: il DB di test resta pulito."""
    async with engine.connect() as conn:
        transaction = await conn.begin()
        async with AsyncSession(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        ) as session:
            yield session
        await transaction.rollback()
