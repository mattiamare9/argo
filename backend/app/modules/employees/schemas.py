import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict

Status = Literal["ACTIVE", "INACTIVE"]


class EmployeeRecord(BaseModel):
    """Un dipendente come lo descrive la fonte ufficiale, già normalizzato."""

    employee_id: str
    email: str
    first_name: str
    last_name: str
    status: Status


class ChangeKind(StrEnum):
    CREATED = "created"
    UPDATED = "updated"  # solo anagrafica (email, nome)
    DEACTIVATED = "deactivated"
    REACTIVATED = "reactivated"
    UNCHANGED = "unchanged"


@dataclass(frozen=True)
class PlannedChange:
    record: EmployeeRecord
    kind: ChangeKind
    profile_changed: bool  # anche un (de)attivazione può portare un cambio di email o nome


@dataclass(frozen=True)
class AppliedChange:
    employee_id: str
    kind: ChangeKind
    status: Status
    profile_changed: bool


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: str
    email: str
    first_name: str
    last_name: str
    status: Status
    source: str
    status_changed_at: datetime


class EmployeePage(BaseModel):
    items: list[EmployeeOut]
    total: int
    page: int
    page_size: int
