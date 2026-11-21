from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Identity, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditEvent(Base):
    """Evento di audit. Append-only: UPDATE/DELETE/TRUNCATE bloccati da trigger (migr. 0001)."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    actor: Mapped[str] = mapped_column(String(200))  # es. "agent:excel-hr", "user:<id>", "worker"
    action: Mapped[str] = mapped_column(String(100))  # es. "employee.deactivated"
    outcome: Mapped[str] = mapped_column(String(20))  # "success" | "failure"
    target_type: Mapped[str | None] = mapped_column(String(50))
    target_id: Mapped[str | None] = mapped_column(String(200))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")

    __table_args__ = (
        Index("ix_audit_events_target", "target_type", "target_id"),
        CheckConstraint("outcome IN ('success', 'failure')", name="outcome"),
    )
