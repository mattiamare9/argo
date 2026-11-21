import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules import audit


async def test_record_persists_event(session: AsyncSession) -> None:
    event = await audit.record(
        session,
        actor="test",
        action="employee.deactivated",
        outcome="success",
        target_type="employee",
        target_id="E001",
        details={"source": "excel-hr"},
    )
    row = (
        await session.execute(
            text("SELECT action, target_id, details FROM audit_events WHERE id = :id"),
            {"id": event.id},
        )
    ).one()
    assert row.action == "employee.deactivated"
    assert row.target_id == "E001"
    assert row.details == {"source": "excel-hr"}
    assert event.occurred_at is not None


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE audit_events SET action = 'tampered'",
        "DELETE FROM audit_events",
        "TRUNCATE audit_events",
    ],
)
async def test_audit_log_is_append_only(session: AsyncSession, statement: str) -> None:
    await audit.record(session, actor="test", action="x", outcome="success")
    with pytest.raises(DBAPIError, match="append-only"):
        async with session.begin_nested():
            await session.execute(text(statement))


async def test_outcome_is_constrained(session: AsyncSession) -> None:
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await audit.record(session, actor="test", action="x", outcome="maybe")  # type: ignore[arg-type]
