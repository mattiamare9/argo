import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Chiave logica (specifica §5.2). `employee_key` è la forma minuscola usata per l'unicità.
    employee_id: Mapped[str] = mapped_column(String(100))
    employee_key: Mapped[str] = mapped_column(String(100), unique=True)
    email: Mapped[str] = mapped_column(String(320))  # salvata in minuscolo
    first_name: Mapped[str] = mapped_column(String(200))
    last_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(10))
    source: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="status"),
        # Verificato a fine transazione: due dipendenti possono scambiarsi l'email in uno snapshot.
        UniqueConstraint("email", deferrable=True, initially="DEFERRED"),
    )
