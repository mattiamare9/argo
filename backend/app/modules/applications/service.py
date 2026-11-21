import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import secrets
from app.core.config import Settings
from app.modules import audit
from app.modules.applications import repository
from app.modules.applications.models import Application
from app.modules.applications.schemas import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationUpdate,
)


class ApplicationNotFound(LookupError):
    pass


class ApplicationConflict(Exception):
    """Operazione non eseguibile nello stato attuale (slug in uso, chiave segreti assente)."""


class InvalidApplication(ValueError):
    """Configurazione incoerente con il connettore."""


# Chiavi di config ammesse per connettore (solo dati non segreti).
CONFIG_KEYS = {"manual": {"notes"}, "scim": {"base_url"}}


def validate_config(connector: str, config: dict[str, Any]) -> None:
    unknown = set(config) - CONFIG_KEYS[connector]
    if unknown:
        raise InvalidApplication(
            f"Campi di configurazione non ammessi: {', '.join(sorted(unknown))}"
        )
    if not all(isinstance(v, str) for v in config.values()):
        raise InvalidApplication("I valori di configurazione devono essere testo")
    if connector == "scim" and not config.get("base_url", "").startswith(("http://", "https://")):
        raise InvalidApplication("Per SCIM serve base_url, un indirizzo http(s)")


def to_out(app: Application) -> ApplicationOut:
    return ApplicationOut(
        id=app.id,
        slug=app.slug,
        name=app.name,
        connector=app.connector,
        config=app.config,
        has_secret=app.secret_ciphertext is not None,
        enabled=app.enabled,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


def _encrypt(settings: Settings, plaintext: str) -> str:
    try:
        return secrets.encrypt(settings, plaintext)
    except secrets.SecretsError as exc:
        raise ApplicationConflict(
            "Non posso salvare il segreto: la chiave di cifratura (ARGO_SECRETS_KEY) "
            "non è configurata o non è valida"
        ) from exc


def _check_secret_allowed(connector: str, secret: str | None) -> None:
    if secret is not None and connector == "manual":
        raise InvalidApplication("Il connettore manuale non usa segreti")


async def _audit(
    db: AsyncSession, actor: str, action: str, app: Application, details: dict
) -> None:
    await audit.record(
        db,
        actor=f"user:{actor}",
        action=action,
        outcome="success",
        target_type="application",
        target_id=str(app.id),
        details={"slug": app.slug, **details},  # mai il segreto
    )


async def list_applications(db: AsyncSession) -> list[ApplicationOut]:
    return [to_out(a) for a in await repository.list_all(db)]


async def get_application(db: AsyncSession, application_id: uuid.UUID) -> Application | None:
    return await repository.get(db, application_id)


async def list_enabled(db: AsyncSession) -> list[Application]:
    return await repository.list_all(db, only_enabled=True)


async def create(
    db: AsyncSession, settings: Settings, data: ApplicationCreate, *, actor: str
) -> ApplicationOut:
    validate_config(data.connector, data.config)
    _check_secret_allowed(data.connector, data.secret)
    if await repository.get_by_slug(db, data.slug):
        raise ApplicationConflict(f"Esiste già un'applicazione con slug «{data.slug}»")
    app = Application(
        slug=data.slug,
        name=data.name,
        connector=data.connector,
        config=data.config,
        enabled=data.enabled,
        secret_ciphertext=_encrypt(settings, data.secret) if data.secret else None,
    )
    db.add(app)
    try:
        await db.flush()
    except IntegrityError as exc:  # creazione concorrente con lo stesso slug
        await db.rollback()
        raise ApplicationConflict(f"Esiste già un'applicazione con slug «{data.slug}»") from exc
    await db.refresh(app)
    await _audit(
        db,
        actor,
        "application.create",
        app,
        {"connector": app.connector, "name": app.name, "has_secret": data.secret is not None},
    )
    await db.commit()
    return to_out(app)


async def update(
    db: AsyncSession,
    settings: Settings,
    application_id: uuid.UUID,
    data: ApplicationUpdate,
    *,
    actor: str,
) -> ApplicationOut:
    app = await repository.get(db, application_id)
    if app is None:
        raise ApplicationNotFound(str(application_id))
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes and data.name is None or "enabled" in changes and data.enabled is None:
        raise InvalidApplication("name ed enabled non possono essere null")
    if data.config is not None:
        validate_config(app.connector, data.config)
    if "secret" in changes:
        _check_secret_allowed(app.connector, data.secret)
        app.secret_ciphertext = _encrypt(settings, data.secret) if data.secret else None
    for field in ("name", "config", "enabled"):
        if changes.get(field) is not None:
            setattr(app, field, changes[field])
    app.updated_at = datetime.now(UTC)
    details: dict[str, Any] = {"fields": sorted(k for k in changes if k != "secret")}
    if "secret" in changes:
        details["secret"] = "set" if data.secret else "cleared"
    await _audit(db, actor, "application.update", app, details)
    await db.commit()
    return to_out(app)


async def delete(db: AsyncSession, application_id: uuid.UUID, *, actor: str) -> None:
    app = await repository.get(db, application_id)
    if app is None:
        raise ApplicationNotFound(str(application_id))
    await _audit(db, actor, "application.delete", app, {"name": app.name})
    await db.delete(app)
    await db.commit()
