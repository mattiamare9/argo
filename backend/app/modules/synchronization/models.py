import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SyncAgent(Base):
    __tablename__ = "sync_agents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)  # SHA-256 della chiave API
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


SNAPSHOT_STATUSES = ("applied", "pending_confirmation", "rejected", "superseded", "cancelled")


class SyncSnapshot(Base):
    __tablename__ = "sync_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)  # snapshot_id scelto dall'agent
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sync_agents.id"), index=True)
    source: Mapped[str] = mapped_column(String(100))
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    status: Mapped[str] = mapped_column(String(30))
    # Conservati per poter applicare dopo la conferma; solo dati anagrafici, nessun segreto.
    records: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    summary: Mapped[dict[str, int]] = mapped_column(JSONB, server_default="{}")
    detail: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[str | None] = mapped_column(String(200))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('applied', 'pending_confirmation', 'rejected', 'superseded', 'cancelled')",
            name="status",
        ),
    )
