import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Application(Base):
    """Applicazione i cui account sono gestiti da Argo (specifica §8.2)."""

    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(63), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    connector: Mapped[str] = mapped_column(String(20))  # manual | scim
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # solo dati non segreti
    secret_ciphertext: Mapped[str | None] = mapped_column(Text)  # cifrato con Fernet
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("connector IN ('manual', 'scim')", name="connector"),
        CheckConstraint("slug ~ '^[a-z0-9-]+$'", name="slug"),
    )
