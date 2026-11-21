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
    MAX_PAGE_SIZE,
    apply_changes,
    count_missing,
    current_status,
    find_email_conflicts,
    key_of,
    list_employees,
    plan_changes,
)

__all__ = [
    "MAX_PAGE_SIZE",
    "AppliedChange",
    "ChangeKind",
    "EmployeeOut",
    "EmployeePage",
    "EmployeeRecord",
    "PlannedChange",
    "apply_changes",
    "count_missing",
    "current_status",
    "find_email_conflicts",
    "key_of",
    "list_employees",
    "plan_changes",
]
