from dataclasses import asdict, dataclass
from typing import Protocol


class SourceError(Exception):
    """The source cannot be read or its content is not valid. The message is user-facing."""


@dataclass(frozen=True)
class EmployeeRecord:
    employee_id: str
    email: str
    first_name: str
    last_name: str
    status: str  # "ACTIVE" | "INACTIVE"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class SourceReader(Protocol):
    def read(self) -> list[EmployeeRecord]:
        """Return the full snapshot, or raise SourceError."""
        ...
