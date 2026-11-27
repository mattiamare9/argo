from .config import FIELDS
from .models import EmployeeRecord, SourceError

MAX_RECORDS = 1000

# Open decision (project spec): "suspend the sync if the file is not updated according to the
# agreed rules" is undefined, so nothing is implemented for it yet.


def valid_email(email: str) -> bool:
    local, sep, domain = email.partition("@")
    return bool(sep and local and "@" not in domain and "." in domain.strip("."))


def build_records(
    rows: list[tuple[int, dict[str, str]]],
    active_values: tuple[str, ...],
    inactive_values: tuple[str, ...],
) -> list[EmployeeRecord]:
    """Validate raw rows (row number, logical field -> text) and map them to records."""
    if not rows:
        raise SourceError("Il file è vuoto: nessuna riga di dati")
    if len(rows) > MAX_RECORDS:
        raise SourceError(f"Troppi dipendenti: {len(rows)} (massimo {MAX_RECORDS})")
    active = {v.strip().lower() for v in active_values}
    inactive = {v.strip().lower() for v in inactive_values}
    records: list[EmployeeRecord] = []
    ids: dict[str, int] = {}
    emails: dict[str, int] = {}
    for number, row in rows:
        for name in FIELDS:
            if not row[name]:
                raise SourceError(f"Riga {number}: campo obbligatorio vuoto ({name})")
        if not valid_email(row["email"]):
            raise SourceError(f"Riga {number}: email non valida ({row['email']})")
        raw_status = row["status"].lower()
        if raw_status in active:
            status = "ACTIVE"
        elif raw_status in inactive:
            status = "INACTIVE"
        else:
            raise SourceError(f"Riga {number}: stato sconosciuto ({row['status']})")
        for seen, key, label in (
            (ids, row["employee_id"].lower(), "employee_id"),
            (emails, row["email"].lower(), "email"),
        ):
            if key in seen:
                raise SourceError(
                    f"Riga {number}: {label} duplicato ({key}), già presente alla riga {seen[key]}"
                )
            seen[key] = number
        records.append(
            EmployeeRecord(
                row["employee_id"], row["email"], row["first_name"], row["last_name"], status
            )
        )
    return records
