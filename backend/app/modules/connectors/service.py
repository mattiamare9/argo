from typing import Protocol

import httpx

from app.core import secrets
from app.core.config import Settings
from app.modules.connectors.manual import ManualConnector
from app.modules.connectors.ports import AppConnector
from app.modules.connectors.scim import ScimConnector
from app.modules.jobs import PermanentError


class AppSpec(Protocol):
    """Quanto serve di un'applicazione (la riga del registro applications)."""

    name: str
    connector: str
    config: dict
    secret_ciphertext: str | None


def build_connector(app: AppSpec, settings: Settings, http: httpx.AsyncClient) -> AppConnector:
    if app.connector == "manual":
        return ManualConnector(app.name)
    if app.connector == "scim":
        if app.secret_ciphertext is None:
            raise PermanentError(f"{app.name}: manca il token SCIM")
        try:
            token = secrets.decrypt(settings, app.secret_ciphertext)
        except secrets.SecretsError as exc:
            raise PermanentError(f"{app.name}: {exc}") from exc
        return ScimConnector(app.config["base_url"], token, http)
    raise PermanentError(f"{app.name}: connettore sconosciuto «{app.connector}»")
