"""Anagrafica dipendenti e loro transizioni di stato. Non conosce fonti né identity provider."""

from app.modules.employees.schemas import (
    AppliedChange,
    ChangeKind,
    EmployeeOut,
    EmployeePage,
    EmployeeRecord,
    PlannedChange,
)
from app.modules.employees.service import (
    apply_changes,
    count_missing,
    find_email_conflicts,
    key_of,
    list_employees,
    plan_changes,
)

__all__ = [
    "AppliedChange",
    "ChangeKind",
    "EmployeeOut",
    "EmployeePage",
    "EmployeeRecord",
    "PlannedChange",
    "apply_changes",
    "count_missing",
    "find_email_conflicts",
    "key_of",
    "list_employees",
    "plan_changes",
]
