import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LifecycleRun(Base):
    """Un'operazione di ciclo di vita su un dipendente; i passi sono job con group_id = id."""

    __tablename__ = "lifecycle_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[str] = mapped_column(String(100), index=True)
    employee_name: Mapped[str] = mapped_column(String(400))
    kind: Mapped[str] = mapped_column(String(30))  # onboarding | offboarding | ...
    triggered_by: Mapped[str] = mapped_column(String(200))
    # Istante reale (non l'inizio della transazione): ordina run creati nello stesso snapshot.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        index=True,
    )
