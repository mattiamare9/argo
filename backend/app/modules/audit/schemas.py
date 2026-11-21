from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    occurred_at: datetime
    actor: str
    action: str
    outcome: str
    target_type: str | None
    target_id: str | None
    details: dict[str, Any]


class AuditPage(BaseModel):
    items: list[AuditEventOut]
    total: int
    page: int
    page_size: int
