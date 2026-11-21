from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurazione da variabili d'ambiente ARGO_* (o file .env in sviluppo)."""

    model_config = SettingsConfigDict(env_prefix="ARGO_", env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    database_url: str
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
