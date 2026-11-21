from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AppAccount:
    employee_id: str
    email: str
    first_name: str
    last_name: str


class AppConnector(Protocol):
    """Account su un'applicazione. Entrambe le operazioni sono idempotenti."""

    async def provision(self, account: AppAccount) -> None: ...

    async def deprovision(self, account: AppAccount) -> None: ...
