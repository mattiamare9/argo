from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurazione da variabili d'ambiente ARGO_* (o file .env in sviluppo)."""

    model_config = SettingsConfigDict(env_prefix="ARGO_", env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    database_url: str
    log_level: str = "INFO"

    # URL pubblico da cui il browser raggiunge la dashboard (redirect OIDC, cookie).
    public_url: str = "http://localhost:5173"

    keycloak_url: str = "http://127.0.0.1:8080"
    keycloak_realm: str = "argo"
    # Service account per l'Admin API (modulo identity).
    keycloak_backend_client_id: str = "argo-backend"
    keycloak_backend_client_secret: SecretStr | None = None
    # Client OIDC della dashboard (modulo sessions).
    oidc_client_id: str = "argo-dashboard"
    oidc_client_secret: SecretStr | None = None

    @property
    def oidc_issuer(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
