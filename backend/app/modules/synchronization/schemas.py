import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.modules.employees import EmployeeRecord

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Email = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
]


class RecordIn(BaseModel):
    employee_id: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ]
    email: Email
    first_name: Text
    last_name: Text
    status: Literal["ACTIVE", "INACTIVE"]

    def to_record(self) -> EmployeeRecord:
        return EmployeeRecord(**self.model_dump())


class SnapshotIn(BaseModel):
    snapshot_id: uuid.UUID
    source: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    read_at: datetime
    records: list[RecordIn] = Field(min_length=1, max_length=1000)


SnapshotStatus = Literal["applied", "pending_confirmation", "duplicate"]


class SnapshotResult(BaseModel):
    snapshot_id: uuid.UUID
    status: SnapshotStatus
    summary: dict[str, int]


class AgentStatusIn(BaseModel):
    ok: bool
    message: Annotated[str, StringConstraints(max_length=1000)] = ""


class AgentOut(BaseModel):
    name: str
    last_seen_at: datetime | None
    last_error: str | None
    last_error_at: datetime | None


class PendingDeactivation(BaseModel):
    employee_id: str
    first_name: str
    last_name: str


class SnapshotOut(BaseModel):
    snapshot_id: uuid.UUID
    agent: str
    received_at: datetime
    status: str
    summary: dict[str, int]
    detail: str | None
    decided_by: str | None


class PendingSnapshotOut(SnapshotOut):
    deactivations: list[PendingDeactivation]


class SyncOverview(BaseModel):
    agents: list[AgentOut]
    pending: PendingSnapshotOut | None
    recent: list[SnapshotOut]
