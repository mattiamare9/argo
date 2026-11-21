import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ConnectorKind = Literal["manual", "scim"]


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(pattern=r"^[a-z0-9-]+$", max_length=63)
    name: str = Field(min_length=1, max_length=200)
    connector: ConnectorKind
    config: dict[str, Any] = Field(default_factory=dict)
    secret: str | None = Field(default=None, min_length=1)
    enabled: bool = True


class ApplicationUpdate(BaseModel):
    """PATCH: `secret` assente = invariato, `null` = rimosso, stringa = nuovo valore."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    config: dict[str, Any] | None = None
    enabled: bool | None = None
    secret: str | None = Field(default=None, min_length=1)


class ApplicationOut(BaseModel):
    """Il segreto non esce mai: solo `has_secret`."""

    id: uuid.UUID
    slug: str
    name: str
    connector: ConnectorKind
    config: dict[str, Any]
    has_secret: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime
